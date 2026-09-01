from enterpriseagent.agent.tools.base import Tool
from enterpriseagent.storage.ticket_repository import TicketRepository


class CreateTicket(Tool):
    def __init__(self, repository: TicketRepository = None) -> None:
        if repository is None:
            self.repository = TicketRepository()
        else:
            self.repository = repository

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
        ticket = self.repository.create(title=title, description=description, priority=priority)
        return f"Ticket #{ticket['id']} created: {ticket['title']}"

    def get_all_tickets(self) -> list[dict]:
        """Retorna todos los tickets con sus IDs"""
        return self.repository.list_all()

    def get_ticket(self, ticket_id: int) -> dict | None:
        """Obtiene un ticket por ID"""
        return self.repository.get(ticket_id)
