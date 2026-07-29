from enterpriseagent.agent.tools.base import Tool


class CreateTicket(Tool):
    def __init__(self) -> None:
        self._tickets: dict[int, dict] = {}
        self._counter: int = 0

    @property
    def name(self) -> str:
        return "create_ticket"

    @property
    def description(self) -> str:
        return "Crea un ticket de soporte técnico"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Título del ticket"},
                "description": {"type": "string", "description": "Descripción del problema"},
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Prioridad",
                },
            },
            "required": ["title", "description"],
        }

    async def execute(self, title: str = "", description: str = "", priority: str = "medium") -> str:
        self._counter += 1
        self._tickets[self._counter] = {
            "title": title,
            "description": description,
            "priority": priority,
        }
        return f"Ticket #{self._counter} created: {title}"
