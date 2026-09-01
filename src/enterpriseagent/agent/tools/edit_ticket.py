from enterpriseagent.agent.tools.base import Tool
from enterpriseagent.storage.ticket_repository import TicketRepository


class EditTicket(Tool):
    def __init__(self, repository: TicketRepository = None) -> None:
        if repository is None:
            self.repository = TicketRepository()
        else:
            self.repository = repository

    @property
    def name(self) -> str:
        return "edit_ticket"

    @property
    def description(self) -> str:
        return "Edita un ticket existente. Especifica el ID del ticket y los campos a actualizar"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "integer", "description": "ID del ticket a editar"},
                "title": {"type": "string", "description": "Nuevo título (opcional)"},
                "description": {"type": "string", "description": "Nueva descripción (opcional)"},
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Nueva prioridad (opcional)",
                },
            },
            "required": ["ticket_id"],
        }

    async def execute(self, ticket_id: int, title: str = None, description: str = None, priority: str = None) -> str:
        success = self.repository.update(
            ticket_id=ticket_id,
            title=title,
            description=description,
            priority=priority
        )
        if success:
            return f"Ticket #{ticket_id} actualizado correctamente"
        else:
            return f"Error: Ticket #{ticket_id} no encontrado"

