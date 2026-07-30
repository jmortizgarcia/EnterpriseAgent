import json
import os
import sqlite3
from datetime import datetime, timezone

SUMMARY_PROMPT = (
    "Resume la siguiente conversación en 2-3 oraciones, conservando datos clave "
    "(nombres, preferencias, decisiones tomadas, tickets creados)."
)

DEFAULT_MAX_TURNS = 20
RECENT_TURNS = 5


class ConversationMemory:
    def __init__(self, db_path: str = "data/sessions.db", max_turns: int = DEFAULT_MAX_TURNS):
        self.max_turns = max_turns
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS sessions ("
            "  session_id TEXT PRIMARY KEY,"
            "  history TEXT NOT NULL,"
            "  summary TEXT NOT NULL DEFAULT '',"
            "  updated_at TEXT NOT NULL"
            ")"
        )
        self._conn.commit()

    def add_turn(self, session_id: str, user_msg: str, assistant_msg: str) -> None:
        history = self._load_history(session_id)
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": assistant_msg})

        if len(history) // 2 > self.max_turns:
            # keep only the most recent
            excess = len(history) - self.max_turns * 2
            history = history[excess:]

        self._save_history(session_id, history)

    def get_context(self, session_id: str) -> list[dict]:
        history = self._load_history(session_id)
        if not history:
            return []

        messages: list[dict] = []
        summary = self._load_summary(session_id)
        if summary:
            messages.append({"role": "system", "content": f"Resumen de la conversación anterior: {summary}"})

        recent = history[-RECENT_TURNS * 2:]
        messages.extend(recent)
        return messages

    def update_summary(self, session_id: str, summary: str) -> None:
        row = self._conn.execute(
            "SELECT session_id FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if row:
            self._conn.execute(
                "UPDATE sessions SET summary = ?, updated_at = ? WHERE session_id = ?",
                (summary, _now(), session_id),
            )
        else:
            self._conn.execute(
                "INSERT INTO sessions (session_id, history, summary, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, "[]", summary, _now()),
            )
        self._conn.commit()

    def _load_history(self, session_id: str) -> list[dict]:
        row = self._conn.execute(
            "SELECT history FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if row:
            return json.loads(row[0])
        return []

    def _load_summary(self, session_id: str) -> str:
        row = self._conn.execute(
            "SELECT summary FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        return row[0] if row and row[0] else ""

    def _save_history(self, session_id: str, history: list[dict]) -> None:
        history_json = json.dumps(history, ensure_ascii=False)
        row = self._conn.execute(
            "SELECT session_id FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if row:
            self._conn.execute(
                "UPDATE sessions SET history = ?, updated_at = ? WHERE session_id = ?",
                (history_json, _now(), session_id),
            )
        else:
            self._conn.execute(
                "INSERT INTO sessions (session_id, history, summary, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, history_json, "", _now()),
            )
        self._conn.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()