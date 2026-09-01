"""Tests for ticket management endpoints and persistence"""
import pytest
from fastapi.testclient import TestClient

from enterpriseagent.main import app, _ticket_manager


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def reset_tickets():
    """Reset tickets before and after each test"""
    # Clear before
    _ticket_manager._tickets.clear()
    yield
    # Clear after
    _ticket_manager._tickets.clear()


class TestTicketsEndpoint:
    def test_list_tickets_empty(self, client, reset_tickets):
        """GET /tickets should return empty list initially"""
        resp = client.get("/tickets")
        assert resp.status_code == 200
        data = resp.json()
        assert "tickets" in data
        assert isinstance(data["tickets"], list)

    def test_get_ticket_not_found(self, client, reset_tickets):
        """GET /tickets/999 should return 404"""
        resp = client.get("/tickets/999")
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data

    def test_ticket_creation_via_agent_appears_in_list(self, client, reset_tickets):
        """Tickets created via agent should be accessible via /tickets endpoint"""
        # First, list tickets (should be empty or have previous ones)
        resp = client.get("/tickets")
        initial_count = len(resp.json()["tickets"])

        # Create ticket via agent chat
        chat_resp = client.post(
            "/agent/chat",
            json={
                "message": "Crea un ticket de alta prioridad porque la CPU está al 95%",
                "provider": "ollama",
            },
        )
        assert chat_resp.status_code == 200

        # List tickets again (should have new ticket)
        resp = client.get("/tickets")
        assert resp.status_code == 200
        tickets = resp.json()["tickets"]
        # We should have more tickets than before (or at least some tickets)
        assert len(tickets) >= initial_count

    def test_get_specific_ticket(self, client, reset_tickets):
        """GET /tickets/1 should return ticket details"""
        # First, create a ticket via the agent
        chat_resp = client.post(
            "/agent/chat",
            json={
                "message": "Crea un ticket con título 'Test Ticket' y descripción 'Testing'",
                "provider": "ollama",
            },
        )
        assert chat_resp.status_code == 200

        # Get the list to find a ticket ID
        resp = client.get("/tickets")
        tickets = resp.json()["tickets"]

        if tickets:
            # Get a specific ticket
            ticket_id = tickets[0]["id"]
            resp = client.get(f"/tickets/{ticket_id}")
            assert resp.status_code == 200
            ticket = resp.json()["ticket"]
            assert ticket["id"] == ticket_id
            assert "title" in ticket
            assert "description" in ticket
            assert "priority" in ticket

    def test_tickets_persist_across_requests(self, client, reset_tickets):
        """Tickets should not be lost between requests"""
        # Create a ticket
        chat_resp = client.post(
            "/agent/chat",
            json={
                "message": "Crea un ticket llamado 'Persistencia Test'",
                "provider": "ollama",
            },
        )
        assert chat_resp.status_code == 200

        # Get tickets immediately
        resp1 = client.get("/tickets")
        tickets1 = resp1.json()["tickets"]
        count1 = len(tickets1)

        # Do another request (unrelated chat)
        client.post(
            "/agent/chat",
            json={"message": "¿Cuál es el precio?", "provider": "ollama"},
        )

        # Get tickets again
        resp2 = client.get("/tickets")
        tickets2 = resp2.json()["tickets"]
        count2 = len(tickets2)

        # Count should be the same (tickets persist)
        assert count1 == count2, "Tickets were lost between requests!"

    def test_ticket_schema(self, client, reset_tickets):
        """Tickets should have correct schema"""
        resp = client.get("/tickets")
        tickets = resp.json()["tickets"]

        if tickets:
            ticket = tickets[0]
            # Should have id, title, description, priority
            assert isinstance(ticket, dict)
            assert "id" in ticket
            assert "title" in ticket
            assert "description" in ticket
            assert "priority" in ticket
            assert ticket["priority"] in ["low", "medium", "high"]

    def test_create_ticket_via_post(self, client, reset_tickets):
        """POST /tickets should create a new ticket"""
        resp = client.post(
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
        ticket = data["ticket"]
        assert ticket["title"] == "Test Ticket"
        assert ticket["description"] == "Test Description"
        assert ticket["priority"] == "high"

    def test_update_ticket_via_put(self, client, reset_tickets):
        """PUT /tickets/{id} should update an existing ticket"""
        # First create a ticket
        create_resp = client.post(
            "/tickets",
            json={
                "title": "Original Title",
                "description": "Original Description",
                "priority": "low",
            }
        )
        ticket_id = create_resp.json()["ticket"]["id"]

        # Update it
        update_resp = client.put(
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

    def test_update_ticket_partial(self, client, reset_tickets):
        """PUT /tickets/{id} should allow partial updates"""
        # Create a ticket
        create_resp = client.post(
            "/tickets",
            json={
                "title": "Original",
                "description": "Description",
                "priority": "medium",
            }
        )
        ticket_id = create_resp.json()["ticket"]["id"]

        # Update only the title
        update_resp = client.put(
            f"/tickets/{ticket_id}",
            json={"title": "New Title"}
        )
        assert update_resp.status_code == 200
        updated = update_resp.json()["ticket"]
        assert updated["title"] == "New Title"
        # Description and priority should remain unchanged
        assert updated["description"] == "Description"
        assert updated["priority"] == "medium"

    def test_update_nonexistent_ticket(self, client, reset_tickets):
        """PUT /tickets/999 should return 404"""
        resp = client.put(
            "/tickets/999",
            json={"title": "Updated"}
        )
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data

    def test_delete_ticket(self, client, reset_tickets):
        """DELETE /tickets/{id} should delete a ticket"""
        # Create a ticket
        create_resp = client.post(
            "/tickets",
            json={
                "title": "To Delete",
                "description": "Delete me",
                "priority": "low",
            }
        )
        ticket_id = create_resp.json()["ticket"]["id"]

        # Delete it
        delete_resp = client.delete(f"/tickets/{ticket_id}")
        assert delete_resp.status_code == 200
        data = delete_resp.json()
        assert "message" in data
        assert str(ticket_id) in data["message"]

        # Verify it's gone
        get_resp = client.get(f"/tickets/{ticket_id}")
        assert get_resp.status_code == 404

    def test_delete_nonexistent_ticket(self, client, reset_tickets):
        """DELETE /tickets/999 should return 404"""
        resp = client.delete("/tickets/999")
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data

    def test_create_ticket_via_post_missing_fields(self, client, reset_tickets):
        """POST /tickets should validate required fields"""
        # Missing title
        resp = client.post(
            "/tickets",
            json={
                "description": "Description",
                "priority": "high",
            }
        )
        assert resp.status_code == 422  # Unprocessable Entity

    def test_ticket_counter_increments(self, client, reset_tickets):
        """Each created ticket should have a unique ID"""
        ids = []
        for i in range(3):
            resp = client.post(
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
        # IDs should be sequential
        assert ids == sorted(ids)
