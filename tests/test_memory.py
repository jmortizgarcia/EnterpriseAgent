import json
import os
import tempfile

import pytest

from enterpriseagent.memory.conversation import ConversationMemory


@pytest.fixture
def db_path():
    tmp = tempfile.mktemp(suffix=".db")
    yield tmp
    try:
        os.remove(tmp)
    except OSError:
        pass


@pytest.fixture
def memory(db_path):
    return ConversationMemory(db_path=db_path, max_turns=3)


class TestConversationMemory:
    def test_add_turn_creates_history(self, memory):
        memory.add_turn("sess-1", "Hola", "Hola, ¿en qué puedo ayudarte?")
        ctx = memory.get_context("sess-1")
        assert len(ctx) == 2
        assert ctx[0]["content"] == "Hola"
        assert ctx[1]["content"] == "Hola, ¿en qué puedo ayudarte?"

    def test_get_context_empty_session(self, memory):
        ctx = memory.get_context("nonexistent")
        assert ctx == []

    def test_multiple_turns_preserved(self, memory):
        memory.add_turn("sess-2", "msg1", "resp1")
        memory.add_turn("sess-2", "msg2", "resp2")
        ctx = memory.get_context("sess-2")
        assert len(ctx) == 4
        assert ctx[2]["content"] == "msg2"
        assert ctx[3]["content"] == "resp2"

    def test_max_turns_sliding_window(self, memory):
        for i in range(5):
            memory.add_turn("sess-3", f"msg{i}", f"resp{i}")
        ctx = memory.get_context("sess-3")
        # max_turns=3 → 3 * 2 = 6 messages max
        assert len(ctx) <= 6
        # oldest message should be gone
        contents = [m["content"] for m in ctx]
        assert "msg0" not in contents
        assert "msg4" in contents

    def test_summary_included_in_context(self, memory):
        memory.add_turn("sess-4", "Hola", "Hola")
        memory.update_summary("sess-4", "Usuario saludó")
        ctx = memory.get_context("sess-4")
        summaries = [m for m in ctx if m.get("role") == "system" and "Resumen" in m["content"]]
        assert len(summaries) == 1
        assert "saludó" in summaries[0]["content"]

    def test_sessions_are_independent(self, memory):
        memory.add_turn("alice", "Hola Alice", "Hola")
        memory.add_turn("bob", "Hola Bob", "Hola")
        ctx_alice = memory.get_context("alice")
        ctx_bob = memory.get_context("bob")
        assert len(ctx_alice) == 2
        assert len(ctx_bob) == 2
        assert "Alice" in ctx_alice[0]["content"]
        assert "Bob" in ctx_bob[0]["content"]

    def test_persistence_across_instances(self, db_path):
        mem1 = ConversationMemory(db_path=db_path)
        mem1.add_turn("persist", "msg", "resp")
        mem2 = ConversationMemory(db_path=db_path)
        ctx = mem2.get_context("persist")
        assert len(ctx) == 2
        assert ctx[0]["content"] == "msg"
        assert ctx[1]["content"] == "resp"

    def test_update_summary_new_session(self, memory):
        memory.update_summary("new-sess", "Resumen inicial")
        ctx = memory.get_context("new-sess")
        assert len(ctx) == 1
        assert "Resumen inicial" in ctx[0]["content"]