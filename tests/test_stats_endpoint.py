from fastapi.testclient import TestClient

from enterpriseagent.main import _stats, app

client = TestClient(app)


class TestStatsEndpoint:
    def setup_method(self):
        _stats.clear()

    def test_stats_empty_session(self):
        resp = client.get("/agent/stats/unknown-session")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_requests"] == 0
        assert data["total_cost"] == 0.0

    def test_stats_with_data(self):
        _stats["test-sess"].append({
            "question": "hola",
            "input_tokens": 50,
            "output_tokens": 30,
            "cost": 0.001,
            "duration_ms": 200.0,
            "provider": "ollama",
            "tool_calls": ["search_docs"],
        })
        _stats["test-sess"].append({
            "question": "adios",
            "input_tokens": 20,
            "output_tokens": 10,
            "cost": 0.0005,
            "duration_ms": 150.0,
            "provider": "ollama",
            "tool_calls": ["create_ticket"],
        })
        resp = client.get("/agent/stats/test-sess")
        data = resp.json()
        assert data["total_requests"] == 2
        assert data["total_tokens"] == 110
        assert data["total_cost"] > 0
        assert data["avg_duration_ms"] > 0
        assert data["tools_used"]["search_docs"] == 1
        assert data["tools_used"]["create_ticket"] == 1

    def test_stats_no_tool_calls(self):
        _stats["no-tool"].append({
            "question": "test",
            "input_tokens": 10,
            "output_tokens": 5,
            "cost": 0.0,
            "duration_ms": 50.0,
            "provider": "ollama",
            "tool_calls": [],
        })
        resp = client.get("/agent/stats/no-tool")
        data = resp.json()
        assert data["tools_used"] == {}

    def test_health_still_works(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
