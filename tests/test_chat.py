import json
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from enterpriseagent.agent.loop import AgentResponse, AgentState
from enterpriseagent.main import app

client = TestClient(app)


class TestChatEndpoint:
    @patch("enterpriseagent.main.run_agent")
    def test_chat_returns_content(self, mock_run_agent):
        mock_run_agent.return_value = AgentResponse(
            content="Hello from agent",
            state=AgentState(messages=[{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello from agent"}]),
            usage={"input_tokens": 10, "output_tokens": 5},
        )
        response = client.post("/agent/chat", json={"message": "Hi"})
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Hello from agent"
        assert data["usage"]["input_tokens"] == 10

    @patch("enterpriseagent.main.get_provider")
    @patch("enterpriseagent.main.run_agent")
    def test_chat_with_openai_provider(self, mock_run_agent, mock_get_provider):
        mock_provider = unittest.mock.AsyncMock()
        mock_get_provider.return_value = mock_provider
        mock_run_agent.return_value = AgentResponse(
            content="OpenAI response",
            state=AgentState(),
        )
        response = client.post("/agent/chat", json={"message": "Hi", "provider": "openai"})
        assert response.status_code == 200
        assert response.json()["content"] == "OpenAI response"

    @patch("enterpriseagent.main.run_agent")
    def test_chat_no_content(self, mock_run_agent):
        mock_run_agent.return_value = AgentResponse(
            content=None,
            state=AgentState(),
        )
        response = client.post("/agent/chat", json={"message": "test"})
        assert response.status_code == 200
        assert response.json()["content"] is None

    def test_chat_missing_message(self):
        response = client.post("/agent/chat", json={})
        assert response.status_code == 422

    def test_chat_extra_fields(self):
        response = client.post("/agent/chat", json={"message": "Hi", "extra": "field"})
        assert response.status_code == 200


class TestChatStreamEndpoint:
    @patch("enterpriseagent.main.run_agent_stream")
    def test_stream_returns_events(self, mock_stream):
        async def mock_events():
            yield {"type": "text", "delta": "Hello"}
            yield {"type": "text", "delta": " world"}

        mock_stream.return_value = mock_events()
        response = client.post("/agent/chat/stream", json={"message": "Hi"})
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        lines = response.text.strip().split("\n\n")
        events = [json.loads(line.replace("data: ", "")) for line in lines if line.startswith("data: ")]
        assert len(events) == 2
        assert events[0]["delta"] == "Hello"

    def test_stream_missing_message(self):
        response = client.post("/agent/chat/stream", json={})
        assert response.status_code == 422
