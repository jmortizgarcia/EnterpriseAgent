import json
import time
from collections import defaultdict
from pathlib import Path

from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from enterpriseagent.agent.loop import run_agent, run_agent_stream
from enterpriseagent.agent.state import AgentState
from enterpriseagent.agent.tools import (
    CreateTicket,
    DeleteTicket,
    EditTicket,
    GetTicket,
    ListTickets,
    QueryMetric,
    SearchDocs,
)
from enterpriseagent.config import settings
from enterpriseagent.guardrails.input import validate_input
from enterpriseagent.guardrails.pii import detect_pii, redact_pii
from enterpriseagent.memory.conversation import ConversationMemory
from enterpriseagent.observability.cost import calculate_cost
from enterpriseagent.observability.logger import log_request
from enterpriseagent.observability.tracing import trace_agent_run
from enterpriseagent.providers import (
    AnthropicProvider,
    LLMProvider,
    OllamaProvider,
    OpenAIProvider,
)
from enterpriseagent.rag.ingestion import chunk_markdown, ingest_docs
from enterpriseagent.rag.vector_store import ChromaStore, get_vector_store
from enterpriseagent.storage.ticket_repository import TicketRepository

app = FastAPI(title="Enterprise Agent", version="0.1.0")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

_memory = ConversationMemory()
_stats: dict[str, list[dict]] = defaultdict(list)
_ticket_repository = TicketRepository()  # Repositorio singleton para persistencia de tickets
_chroma_store = ChromaStore()  # RAG vector store singleton


@app.middleware("http")
async def guardrails_middleware(request: Request, call_next):
    if request.url.path in ("/agent/chat", "/agent/chat/stream"):
        raw = await request.body()
        body = json.loads(raw)
        message = body.get("message")

        if message is not None:
            input_val = validate_input(message)
            if input_val.blocked:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Message blocked", "reason": input_val.reason},
                )

            pii = detect_pii(message)
            if pii.has_pii:
                body["message"] = redact_pii(message, pii)
                request._body = json.dumps(body).encode()

    response = await call_next(request)
    return response


class ChatRequest(BaseModel):
    message: str
    provider: str | None = None
    session_id: str = ""


class ChatResponse(BaseModel):
    content: str | None
    usage: dict | None = None
    session_id: str = ""


class CreateTicketRequest(BaseModel):
    title: str
    description: str
    priority: str = "medium"


class UpdateTicketRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: str | None = None


def get_provider(name: str | None = None) -> LLMProvider:
    provider_name = name or settings.provider
    if provider_name == "openai":
        return OpenAIProvider()
    if provider_name == "ollama":
        return OllamaProvider()
    return AnthropicProvider()


def get_tools() -> list:
    store = get_vector_store()
    # Usar el repositorio singleton compartido por todos los tools
    return [
        SearchDocs(store=store),
        CreateTicket(_ticket_repository),
        EditTicket(_ticket_repository),
        GetTicket(_ticket_repository),
        ListTickets(_ticket_repository),
        DeleteTicket(_ticket_repository),
        QueryMetric()
    ]


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/agent/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    provider = get_provider(request.provider)
    tools = get_tools()
    session_id = request.session_id or ""
    t0 = time.monotonic()

    context_messages = _memory.get_context(session_id) if session_id else []
    result = await run_agent(
        user_message=request.message,
        provider=provider,
        tools=tools,
        state=AgentState(messages=context_messages) if context_messages else None,
    )

    duration_ms = (time.monotonic() - t0) * 1000
    usage = result.usage or {}
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    provider_name = request.provider or settings.provider
    cost = calculate_cost(provider_name, input_tokens, output_tokens)

    if session_id and result.content:
        _memory.add_turn(session_id, request.message, result.content)
        _stats[session_id].append({
            "question": request.message,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "duration_ms": duration_ms,
            "provider": provider_name,
            "tool_calls": [],
        })

    log_request(session_id, provider_name, input_tokens, output_tokens, cost, duration_ms)
    await trace_agent_run(
        session_id, request.message, result.content,
        provider_name, input_tokens, output_tokens, cost, duration_ms,
    )

    return ChatResponse(content=result.content, usage=result.usage, session_id=session_id)


@app.post("/agent/chat/stream")
async def chat_stream(request: ChatRequest):
    provider = get_provider(request.provider)
    tools = get_tools()
    session_id = request.session_id or ""
    t0 = time.monotonic()

    context_messages = _memory.get_context(session_id) if session_id else []

    async def event_stream():
        full_response = ""
        async for event in run_agent_stream(
            user_message=request.message,
            provider=provider,
            tools=tools,
            state=AgentState(messages=context_messages) if context_messages else None,
        ):
            if event.get("type") == "content":
                full_response += event.get("content", "")
            yield f"data: {json.dumps(event)}\n\n"

        duration_ms = (time.monotonic() - t0) * 1000
        provider_name = request.provider or settings.provider

        if session_id and full_response:
            _memory.add_turn(session_id, request.message, full_response)

        log_request(session_id, provider_name, duration_ms=duration_ms)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
    )


@app.get("/agent/history/{session_id}")
async def get_session_history(session_id: str):
    """Get full conversation history for a session"""
    # Get the full history, not just recent context
    history = _memory._load_history(session_id)
    return {"messages": history or [], "session_id": session_id}


@app.get("/agent/stats/{session_id}")
async def get_session_stats(session_id: str):
    entries = _stats.get(session_id, [])
    if not entries:
        return {
            "session_id": session_id,
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "avg_duration_ms": 0.0,
            "tools_used": {},
        }

    total_input = sum(e.get("input_tokens", 0) for e in entries)
    total_output = sum(e.get("output_tokens", 0) for e in entries)
    total_cost = sum(e.get("cost", 0.0) for e in entries)
    total_duration = sum(e.get("duration_ms", 0.0) for e in entries)

    all_tools: list[str] = []
    for e in entries:
        all_tools.extend(e.get("tool_calls", []))
    tools_used: dict[str, int] = {}
    for t in all_tools:
        tools_used[t] = tools_used.get(t, 0) + 1

    return {
        "session_id": session_id,
        "total_requests": len(entries),
        "total_tokens": total_input + total_output,
        "total_cost": round(total_cost, 6),
        "avg_duration_ms": round(total_duration / len(entries), 2) if entries else 0.0,
        "tools_used": tools_used,
    }


@app.get("/agent/sessions")
async def list_all_sessions():
    """List all sessions with metadata (for history viewer)"""
    sessions = _memory.list_all_sessions()
    return {"sessions": sessions, "total": len(sessions)}


@app.get("/tickets")
async def list_tickets():
    """Lista todos los tickets creados"""
    return {"tickets": _ticket_repository.list_all()}


@app.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: int):
    """Obtiene un ticket específico por ID"""
    ticket = _ticket_repository.get(ticket_id)
    if not ticket:
        return JSONResponse(
            status_code=404,
            content={"error": "Ticket not found", "ticket_id": ticket_id}
        )
    return {"ticket": ticket}


@app.post("/tickets")
async def create_ticket(request: CreateTicketRequest):
    """Crea un nuevo ticket"""
    ticket = _ticket_repository.create(
        title=request.title,
        description=request.description,
        priority=request.priority
    )
    message = f"Ticket #{ticket['id']} created: {ticket['title']}"
    return {"ticket": ticket, "message": message}


@app.put("/tickets/{ticket_id}")
async def update_ticket(ticket_id: int, request: UpdateTicketRequest):
    """Actualiza un ticket existente"""
    success = _ticket_repository.update(
        ticket_id=ticket_id,
        title=request.title,
        description=request.description,
        priority=request.priority
    )
    if not success:
        return JSONResponse(
            status_code=404,
            content={"error": "Ticket not found", "ticket_id": ticket_id}
        )
    ticket = _ticket_repository.get(ticket_id)
    return {"ticket": ticket, "message": f"Ticket #{ticket_id} updated"}


@app.delete("/tickets/{ticket_id}")
async def delete_ticket(ticket_id: int):
    """Elimina un ticket"""
    success = _ticket_repository.delete(ticket_id)
    if not success:
        return JSONResponse(
            status_code=404,
            content={"error": "Ticket not found", "ticket_id": ticket_id}
        )
    return {"message": f"Ticket #{ticket_id} deleted", "ticket_id": ticket_id}


# ============= RAG ENDPOINTS =============

@app.get("/rag/documents")
async def list_rag_documents():
    """List all indexed documents in ChromaDB"""
    try:
        docs = _chroma_store.get_all_documents()
        info = _chroma_store.get_collection_info()
        return {
            "documents": docs,
            "collection_info": info,
            "total_chunks": len(docs),
        }
    except OSError as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"{e!s}"}
        )


@app.get("/rag/stats")
async def get_rag_stats():
    """Get RAG collection statistics"""
    try:
        info = _chroma_store.get_collection_info()
        return info
    except OSError as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"{e!s}"}
        )



@app.post("/rag/upload")
async def upload_documentation(file: UploadFile):
    """Upload and ingest a markdown file into RAG"""
    try:
        if not file.filename.endswith(".md"):
            return JSONResponse(
                status_code=400,
                content={"error": "Only .md files are supported"}
            )

        content = await file.read()
        text_content = content.decode("utf-8")

        # Chunk and ingest
        chunks = chunk_markdown(text_content, source=file.filename)
        if not chunks:
            return JSONResponse(
                status_code=400,
                content={"error": "No content extracted from file"}
            )

        await _chroma_store.add(chunks)

        return {
            "message": f"Successfully ingested {file.filename}",
            "chunks_added": len(chunks),
            "source": file.filename,
        }
    except OSError as e:  # Changed from bare Exception
        return JSONResponse(
            status_code=500,
            content={"error": f"Upload failed: {e!s}"}
        )


@app.post("/rag/reindex")
async def reindex_documentation():
    """Reindex all documentation from data/docs directory"""
    try:
        result = await ingest_docs()
        return {
            "message": "Reindexing complete",
            "details": result,
        }
    except OSError as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Reindexing failed: {e!s}"}
        )

