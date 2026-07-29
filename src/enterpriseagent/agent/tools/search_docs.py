from enterpriseagent.agent.tools.base import Tool


class SearchDocs(Tool):
    @property
    def name(self) -> str:
        return "search_docs"

    @property
    def description(self) -> str:
        return "Busca información en la documentación técnica"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Consulta de búsqueda",
                },
            },
            "required": ["query"],
        }

    async def execute(self, query: str = "") -> str:
        return f"[Stub] Simulated search for: {query}"
