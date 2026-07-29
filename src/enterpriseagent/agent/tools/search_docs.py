from enterpriseagent.agent.tools.base import Tool
from enterpriseagent.rag.vector_store import ChromaStore


class SearchDocs(Tool):
    def __init__(self, store: ChromaStore | None = None):
        self._store = store or ChromaStore()

    @property
    def name(self) -> str:
        return "search_docs"

    @property
    def description(self) -> str:
        return "Busca información en la documentación técnica de Nimbus Cloud Platform"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Consulta de búsqueda en lenguaje natural",
                },
            },
            "required": ["query"],
        }

    async def execute(self, query: str = "") -> str:
        results = await self._store.similarity_search(query, k=5)
        if not results:
            return "No se encontraron resultados en la documentación."
        lines: list[str] = []
        for i, r in enumerate(results, 1):
            source = r.metadata.get("source", "?")
            section = r.metadata.get("section", "")
            snippet = r.text[:200].replace("\n", " ").strip()
            lines.append(f"[{i}] {source} > {section}: {snippet}")
        return "\n\n".join(lines)
