import sqlite3
import time
from pathlib import Path


class TicketRepository:
    """Repositorio de tickets persistente usando SQLite"""

    def __init__(self, db_path: str = "./data/tickets.db"):
        # Crear directorio si no existe (excepto para :memory:)
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Conectar a la base de datos
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Acceso por nombre de columna
        self._create_table()

    def _create_table(self):
        """Crea la tabla de tickets si no existe"""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL DEFAULT 'medium'
            )
        """)
        self.conn.commit()

    def create(self, title: str = "", description: str = "", priority: str = "medium") -> dict:
        """Crea un nuevo ticket y retorna el ticket creado"""
        # Usar defaults si están vacíos
        if not title:
            title = "Ticket sin título"
        if not description:
            description = "Sin descripción"
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO tickets (title, description, priority)
            VALUES (?, ?, ?)
        """, (title, description, priority))
        self.conn.commit()
        
        ticket_id = cursor.lastrowid
        return self.get(ticket_id)

    def get(self, ticket_id: int) -> dict | None:
        """Obtiene un ticket por ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, title, description, priority FROM tickets WHERE id = ?", (ticket_id,))
        row = cursor.fetchone()
        
        if row:
            return {
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "priority": row["priority"]
            }
        return None

    def list_all(self) -> list[dict]:
        """Retorna todos los tickets ordenados por ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, title, description, priority FROM tickets ORDER BY id")
        rows = cursor.fetchall()
        
        return [
            {
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "priority": row["priority"]
            }
            for row in rows
        ]

    def update(self, ticket_id: int, title: str = None, 
               description: str = None, priority: str = None) -> bool:
        """Actualiza un ticket. Retorna True si fue exitoso, False si no existe"""
        # Verificar que el ticket existe
        if not self.get(ticket_id):
            return False
        
        # Construir UPDATE dinámico
        updates = []
        params = []
        
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if priority is not None and priority in ["low", "medium", "high"]:
            updates.append("priority = ?")
            params.append(priority)
        
        if not updates:
            return True  # Nada que actualizar, pero no es error
        
        params.append(ticket_id)
        query = f"UPDATE tickets SET {', '.join(updates)} WHERE id = ?"
        
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        self.conn.commit()
        
        return True

    def delete(self, ticket_id: int) -> bool:
        """Elimina un ticket. Retorna True si fue exitoso, False si no existe"""
        if not self.get(ticket_id):
            return False
        
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))
        self.conn.commit()
        
        return True

    def close(self):
        """Cierra la conexión a la base de datos"""
        self.conn.close()
