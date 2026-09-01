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

    def get_all_tickets(self) -> list[dict]:
        """Retorna todos los tickets con sus IDs"""
        return [{"id": tid, **data} for tid, data in self._tickets.items()]

    def get_ticket(self, ticket_id: int) -> dict | None:
        """Obtiene un ticket por ID"""
        if ticket_id in self._tickets:
            return {"id": ticket_id, **self._tickets[ticket_id]}
        return None

    def edit_ticket(self, ticket_id: int, title: str = None, description: str = None, priority: str = None) -> bool:
        """Edita un ticket existente. Retorna True si fue exitoso, False si no existe."""
        if ticket_id not in self._tickets:
            return False
        
        if title is not None:
            self._tickets[ticket_id]["title"] = title
        if description is not None:
            self._tickets[ticket_id]["description"] = description
        if priority is not None and priority in ["low", "medium", "high"]:
            self._tickets[ticket_id]["priority"] = priority
        
        return True

    def delete_ticket(self, ticket_id: int) -> bool:
        """Elimina un ticket. Retorna True si fue exitoso, False si no existe."""
        if ticket_id not in self._tickets:
            return False
        del self._tickets[ticket_id]
        return True
