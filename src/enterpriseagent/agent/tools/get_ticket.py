from enterpriseagent.agent.tools.base import Tool
from enterpriseagent.storage.ticket_repository import TicketRepository


class GetTicket(Tool):
    def __init__(self, repository: TicketRepository = None) -> None:
        if repository is None:
            self.repository = TicketRepository()
        else:
            self.repository = repository

    @property
    def name(self) -> str:
        return "get_ticket"

    @property
    def description(self) -> str:
        return "Obtiene los detalles de un ticket específico por su ID"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "integer", "description": "ID del ticket a obtener"}
            },
            "required": ["ticket_id"]
        }

    async def execute(self, ticket_id: int) -> str:
        ticket = self.repository.get(ticket_id)
        
        if not ticket:
            return f"Ticket #{ticket_id} no encontrado"
        
        lines = [
            f"Ticket #{ticket['id']}",
            f"Título: {ticket['title']}",
            f"Descripción: {ticket['description']}",
            f"Prioridad: {ticket['priority']}"
        ]
        
        return "\n".join(lines)
