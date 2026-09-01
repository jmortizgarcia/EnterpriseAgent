from enterpriseagent.agent.tools.base import Tool
from enterpriseagent.storage.ticket_repository import TicketRepository


class DeleteTicket(Tool):
    def __init__(self, repository: TicketRepository = None) -> None:
        if repository is None:
            self.repository = TicketRepository()
        else:
            self.repository = repository

    @property
    def name(self) -> str:
        return "delete_ticket"

    @property
    def description(self) -> str:
        return "Elimina un ticket existente por su ID"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "integer", "description": "ID del ticket a eliminar"}
            },
            "required": ["ticket_id"]
        }

    async def execute(self, ticket_id: int) -> str:
        success = self.repository.delete(ticket_id)
        
        if success:
            return f"Ticket #{ticket_id} eliminado correctamente"
        else:
            return f"Error: Ticket #{ticket_id} no encontrado"
