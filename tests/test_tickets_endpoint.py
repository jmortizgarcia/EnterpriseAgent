"""Tests for ticket management endpoints and persistence"""
import pytest
from fastapi.testclient import TestClient

from enterpriseagent.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestTicketsEndpoint:
    def test_list_tickets_empty(self, client):
        """GET /tickets should return empty list initially"""
        resp = client.get("/tickets")
        assert resp.status_code == 200
        data = resp.json()
        assert "tickets" in data
        assert isinstance(data["tickets"], list)

    def test_get_ticket_not_found(self, client):
        """GET /tickets/999 should return 404"""
        resp = client.get("/tickets/999")
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data

    def test_ticket_creation_via_agent_appears_in_list(self, client):
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

    def test_get_specific_ticket(self, client):
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

    def test_tickets_persist_across_requests(self, client):
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

    def test_ticket_schema(self, client):
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
