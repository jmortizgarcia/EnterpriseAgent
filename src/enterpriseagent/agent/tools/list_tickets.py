from enterpriseagent.agent.tools.base import Tool
from enterpriseagent.storage.ticket_repository import TicketRepository


class ListTickets(Tool):
    def __init__(self, repository: TicketRepository = None) -> None:
        if repository is None:
            self.repository = TicketRepository()
        else:
            self.repository = repository

    @property
    def name(self) -> str:
        return "list_tickets"

    @property
    def description(self) -> str:
        return "Lista todos los tickets existentes"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    async def execute(self) -> str:
        tickets = self.repository.list_all()
        
        if not tickets:
            return "No hay tickets."
        
        lines = ["Tickets encontrados:"]
        for ticket in tickets:
            lines.append(
                f"#{ticket['id']}: {ticket['title']} "
                f"(prioridad: {ticket['priority']})"
            )
        
        return "\n".join(lines)
