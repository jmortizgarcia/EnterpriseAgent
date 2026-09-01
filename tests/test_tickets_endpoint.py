"""Tests for ticket management endpoints with SQLite persistence"""
import sys
import pytest
from fastapi.testclient import TestClient

from enterpriseagent.main import app
from enterpriseagent.storage.ticket_repository import TicketRepository


@pytest.fixture
def test_repository():
    """Crea un repositorio temporal en memoria para tests"""
    repo = TicketRepository(db_path=":memory:")
    yield repo
    repo.close()


@pytest.fixture
def client_with_repo(test_repository, monkeypatch):
    """Cliente TestClient que usa el repositorio en memoria"""
    # Reemplazar el repositorio global con el de prueba
    main_module = sys.modules["enterpriseagent.main"]
    monkeypatch.setattr(main_module, "_ticket_repository", test_repository)
    
    return TestClient(app)


class TestTicketsEndpoint:
    def test_list_tickets_empty(self, client_with_repo, test_repository):
        """GET /tickets should return empty list initially"""
        resp = client_with_repo.get("/tickets")
        assert resp.status_code == 200
        data = resp.json()
        assert "tickets" in data
        assert isinstance(data["tickets"], list)
        assert len(data["tickets"]) == 0

    def test_get_ticket_not_found(self, client_with_repo, test_repository):
        """GET /tickets/999 should return 404"""
        resp = client_with_repo.get("/tickets/999")
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data

    def test_get_specific_ticket(self, client_with_repo, test_repository):
        """GET /tickets/1 should return ticket details"""
        # Create a ticket via POST
        create_resp = client_with_repo.post(
            "/tickets",
            json={
                "title": "Test Ticket",
                "description": "Testing",
                "priority": "medium",
            }
        )
        assert create_resp.status_code == 200
        ticket_id = create_resp.json()["ticket"]["id"]

        # Get the specific ticket
        resp = client_with_repo.get(f"/tickets/{ticket_id}")
        assert resp.status_code == 200
        ticket = resp.json()["ticket"]
        assert ticket["id"] == ticket_id
        assert ticket["title"] == "Test Ticket"
        assert "description" in ticket
        assert "priority" in ticket

    def test_ticket_schema(self, client_with_repo, test_repository):
        """Tickets should have correct schema"""
        # Create a ticket
        resp = client_with_repo.post(
            "/tickets",
            json={
                "title": "Schema Test",
                "description": "Testing schema",
                "priority": "high",
            }
        )
        
        tickets_resp = client_with_repo.get("/tickets")
        tickets = tickets_resp.json()["tickets"]

        if tickets:
            ticket = tickets[0]
            # Should have id, title, description, priority
            assert isinstance(ticket, dict)
            assert "id" in ticket
            assert "title" in ticket
            assert "description" in ticket
            assert "priority" in ticket
            assert ticket["priority"] in ["low", "medium", "high"]

    def test_create_ticket_via_post(self, client_with_repo, test_repository):
        """POST /tickets should create a new ticket"""
        resp = client_with_repo.post(
            "/tickets",
            json={
                "title": "Test Ticket",
                "description": "Test Description",
                "priority": "high",
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "ticket" in data
        assert "message" in data
        ticket = data["ticket"]
        assert ticket["title"] == "Test Ticket"
        assert ticket["description"] == "Test Description"
        assert ticket["priority"] == "high"
        assert ticket["id"] == 1

    def test_update_ticket_via_put(self, client_with_repo, test_repository):
        """PUT /tickets/{id} should update an existing ticket"""
        # First create a ticket
        create_resp = client_with_repo.post(
            "/tickets",
            json={
                "title": "Original Title",
                "description": "Original Description",
                "priority": "low",
            }
        )
        ticket_id = create_resp.json()["ticket"]["id"]

        # Update it
        update_resp = client_with_repo.put(
            f"/tickets/{ticket_id}",
            json={
                "title": "Updated Title",
                "description": "Updated Description",
                "priority": "high",
            }
        )
        assert update_resp.status_code == 200
        updated = update_resp.json()["ticket"]
        assert updated["title"] == "Updated Title"
        assert updated["description"] == "Updated Description"
        assert updated["priority"] == "high"

    def test_update_ticket_partial(self, client_with_repo, test_repository):
        """PUT /tickets/{id} should allow partial updates"""
        # Create a ticket
        create_resp = client_with_repo.post(
            "/tickets",
            json={
                "title": "Original",
                "description": "Description",
                "priority": "medium",
            }
        )
        ticket_id = create_resp.json()["ticket"]["id"]

        # Update only the title
        update_resp = client_with_repo.put(
            f"/tickets/{ticket_id}",
            json={"title": "New Title"}
        )
        assert update_resp.status_code == 200
        updated = update_resp.json()["ticket"]
        assert updated["title"] == "New Title"
        # Description and priority should remain unchanged
        assert updated["description"] == "Description"
        assert updated["priority"] == "medium"

    def test_update_nonexistent_ticket(self, client_with_repo, test_repository):
        """PUT /tickets/999 should return 404"""
        resp = client_with_repo.put(
            "/tickets/999",
            json={"title": "Updated"}
        )
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data

    def test_delete_ticket(self, client_with_repo, test_repository):
        """DELETE /tickets/{id} should delete a ticket"""
        # Create a ticket
        create_resp = client_with_repo.post(
            "/tickets",
            json={
                "title": "To Delete",
                "description": "Delete me",
                "priority": "low",
            }
        )
        ticket_id = create_resp.json()["ticket"]["id"]

        # Delete it
        delete_resp = client_with_repo.delete(f"/tickets/{ticket_id}")
        assert delete_resp.status_code == 200
        data = delete_resp.json()
        assert "message" in data
        assert str(ticket_id) in data["message"]

        # Verify it's gone
        get_resp = client_with_repo.get(f"/tickets/{ticket_id}")
        assert get_resp.status_code == 404

    def test_delete_nonexistent_ticket(self, client_with_repo, test_repository):
        """DELETE /tickets/999 should return 404"""
        resp = client_with_repo.delete("/tickets/999")
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data

    def test_create_ticket_via_post_missing_fields(self, client_with_repo, test_repository):
        """POST /tickets should validate required fields"""
        # Missing title
        resp = client_with_repo.post(
            "/tickets",
            json={
                "description": "Description",
                "priority": "high",
            }
        )
        assert resp.status_code == 422  # Unprocessable Entity

    def test_ticket_counter_increments(self, client_with_repo, test_repository):
        """Each created ticket should have a unique autoincrement ID"""
        ids = []
        for i in range(3):
            resp = client_with_repo.post(
                "/tickets",
                json={
                    "title": f"Ticket {i}",
                    "description": f"Description {i}",
                }
            )
            ticket_id = resp.json()["ticket"]["id"]
            ids.append(ticket_id)

        # All IDs should be unique
        assert len(set(ids)) == 3
        # IDs should be sequential (1, 2, 3)
        assert ids == [1, 2, 3]

    def test_ticket_persistence_in_db(self, test_repository):
        """Tickets should persist in SQLite database"""
        # Create a ticket
        ticket1 = test_repository.create(
            title="Persistent Ticket",
            description="This should persist",
            priority="high"
        )
        ticket_id = ticket1["id"]

        # Retrieve it
        ticket2 = test_repository.get(ticket_id)
        assert ticket2 is not None
        assert ticket2["title"] == "Persistent Ticket"
        assert ticket2["description"] == "This should persist"
        assert ticket2["priority"] == "high"

    def test_list_tickets_after_create(self, client_with_repo, test_repository):
        """GET /tickets should include created tickets"""
        # Create 3 tickets
        for i in range(3):
            client_with_repo.post(
                "/tickets",
                json={
                    "title": f"Ticket {i}",
                    "description": f"Description {i}",
                    "priority": "medium",
                }
            )

        # List all
        resp = client_with_repo.get("/tickets")
        assert resp.status_code == 200
        tickets = resp.json()["tickets"]
        assert len(tickets) == 3

    def test_default_values_for_empty_fields(self, client_with_repo, test_repository):
        """Empty title/description should use defaults"""
        resp = client_with_repo.post(
            "/tickets",
            json={
                "title": "",
                "description": "",
                "priority": "medium",
            }
        )
        assert resp.status_code == 200
        ticket = resp.json()["ticket"]
        assert ticket["title"] == "Ticket sin título"
        assert ticket["description"] == "Sin descripción"
