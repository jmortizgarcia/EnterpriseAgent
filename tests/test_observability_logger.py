import json
import logging
import re

from enterpriseagent.observability.logger import JSONFormatter


class TestJSONFormatter:
    def test_format_basic_record(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["message"] == "test message"
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test"

    def test_format_with_extra_fields(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py",
            lineno=1, msg="request", args=(), exc_info=None,
        )
        record.session_id = "sess-123"
        record.provider = "claude"
        record.input_tokens = 100
        record.cost = 0.001
        output = json.loads(formatter.format(record))
        assert output["session_id"] == "sess-123"
        assert output["provider"] == "claude"
        assert output["input_tokens"] == 100
        assert output["cost"] == 0.001

    def test_output_is_json(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="x", level=logging.INFO, pathname="x.py",
            lineno=1, msg="hello", args=(), exc_info=None,
        )
        output = formatter.format(record)
        json.loads(output)

    def test_timestamp_format(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="x", level=logging.INFO, pathname="x.py",
            lineno=1, msg="m", args=(), exc_info=None,
        )
        output = json.loads(formatter.format(record))
        assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", output["timestamp"])
