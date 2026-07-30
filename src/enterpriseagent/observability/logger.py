from __future__ import annotations

import json
import logging
import sys


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("session_id", "provider", "input_tokens", "output_tokens", "cost", "duration_ms", "tool_calls"):
            val = getattr(record, key, None)
            if val is not None:
                obj[key] = val
        return json.dumps(obj, ensure_ascii=False)


_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(JSONFormatter())

_logger = logging.getLogger("enterpriseagent")
_logger.setLevel(logging.INFO)
_logger.addHandler(_handler)
_logger.propagate = False


def get_logger() -> logging.Logger:
    return _logger


def log_request(
    session_id: str,
    provider: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost: float = 0.0,
    duration_ms: float = 0.0,
    tool_calls: list[str] | None = None,
) -> None:
    extra = {
        "session_id": session_id,
        "provider": provider,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost": cost,
        "duration_ms": duration_ms,
        "tool_calls": tool_calls or [],
    }
    _logger.info("agent_request", extra=extra)
