from __future__ import annotations

from dataclasses import dataclass

import chromadb
import httpx
from chromadb import PersistentClient

from enterpriseagent.config import settings


@dataclass
class ScoredChunk:
    text: str
    score: float
    metadata: dict


class ChromaStore:
    def __init__(self, path: str = "./data/chroma") -> None:
        self.client: PersistentClient = chromadb.PersistentClient(path)
        self.collection = self.client.get_or_create_collection(
            name="docs",
            metadata={"hnsw:space": "cosine"},
        )

    async def add(self, chunks: list[dict]) -> None:
        texts = [c["text"] for c in chunks]
        metadatas = [c.get("metadata", {}) for c in chunks]
        ids = [c["id"] for c in chunks]
        embeddings = await self._embed(texts)
        self.collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    async def similarity_search(self, query: str, k: int = 5) -> list[ScoredChunk]:
        query_embedding = await self._embed([query])
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=k,
        )
        chunks: list[ScoredChunk] = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                chunks.append(
                    ScoredChunk(
                        text=doc,
                        score=results["distances"][0][i] if results["distances"] else 0.0,
                        metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                    )
                )
        return chunks

    async def _embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/embed",
                json={"model": settings.embedding_model, "input": texts},
            )
            resp.raise_for_status()
            data = resp.json()
            return data["embeddings"]

    def get_all_documents(self) -> list[dict]:
        """Get all indexed documents with metadata"""
        docs = self.collection.get(include=["embeddings", "metadatas", "documents"])
        result = []
        if docs and docs["ids"]:
            for i, doc_id in enumerate(docs["ids"]):
                result.append({
                    "id": doc_id,
                    "text": docs["documents"][i] if docs["documents"] else "",
                    "metadata": docs["metadatas"][i] if docs["metadatas"] else {},
                })
        return result

    def get_collection_info(self) -> dict:
        """Get collection statistics"""
        docs = self.collection.get(include=[])
        return {
            "name": "docs",
            "count": len(docs.get("ids", [])),
            "embedding_model": settings.embedding_model,
        }


class PgVectorStore:
    VECTOR_DIM = 768

    def __init__(self, database_url: str | None = None) -> None:
        self._url = database_url or settings.database_url_pg
        self._engine = None
        self._initialized = False

    async def _ensure_setup(self) -> None:
        if self._initialized:
            return
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker

        self._engine = create_engine(self._url)
        Session = sessionmaker(bind=self._engine)
        with Session() as session:
            session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata JSONB DEFAULT '{}',
                    embedding vector(768)
                )
            """))
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_documents_embedding
                ON documents USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """))
            session.commit()
        self._initialized = True

    async def add(self, chunks: list[dict]) -> None:
        from sqlalchemy import text

        await self._ensure_setup()
        texts = [c["text"] for c in chunks]
        embeddings = await self._embed(texts)
        from sqlalchemy.orm import sessionmaker

        Session = sessionmaker(bind=self._engine)
        with Session() as session:
            for i, chunk in enumerate(chunks):
                emb = embeddings[i]
                emb_str = "[" + ",".join(str(x) for x in emb) + "]"
                session.execute(
                    text("""
                        INSERT INTO documents (id, content, metadata, embedding)
                        VALUES (:id, :content, :metadata, :embedding::vector)
                        ON CONFLICT (id) DO UPDATE
                        SET content = EXCLUDED.content,
                            metadata = EXCLUDED.metadata,
                            embedding = EXCLUDED.embedding
                    """),
                    {
                        "id": chunk["id"],
                        "content": chunk["text"],
                        "metadata": str(chunk.get("metadata", {})),
                        "embedding": emb_str,
                    },
                )
            session.commit()

    async def similarity_search(self, query: str, k: int = 5) -> list[ScoredChunk]:
        from sqlalchemy import text
        from sqlalchemy.orm import sessionmaker

        await self._ensure_setup()
        query_embedding = (await self._embed([query]))[0]
        emb_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
        Session = sessionmaker(bind=self._engine)
        with Session() as session:
            rows = session.execute(
                text("""
                    SELECT content, metadata,
                           1 - (embedding <=> :embedding::vector) AS score
                    FROM documents
                    ORDER BY embedding <=> :embedding::vector
                    LIMIT :k
                """),
                {"embedding": emb_str, "k": k},
            ).fetchall()
        return [
            ScoredChunk(text=row[0], score=row[2], metadata=row[1] or {})
            for row in rows
        ]

    async def _embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/embed",
                json={"model": settings.embedding_model, "input": texts},
            )
            resp.raise_for_status()
            data = resp.json()
            return data["embeddings"]


def get_vector_store() -> ChromaStore | PgVectorStore:
    if settings.vector_store == "pgvector":
        return PgVectorStore()
    return ChromaStore()
