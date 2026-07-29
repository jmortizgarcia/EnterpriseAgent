import pytest

from enterpriseagent.agent.tools import CreateTicket, QueryMetric, SearchDocs
from enterpriseagent.agent.tools.base import Tool as ToolABC


class TestToolABC:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            ToolABC()


class TestSearchDocs:
    @pytest.fixture
    def tool(self):
        return SearchDocs()

    def test_name(self, tool):
        assert tool.name == "search_docs"

    def test_description(self, tool):
        assert len(tool.description) > 0

    def test_input_schema(self, tool):
        schema = tool.input_schema
        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        assert "query" in schema["required"]

    @pytest.mark.asyncio
    async def test_execute(self, tool):
        result = await tool.execute(query="how to deploy")
        assert "Simulated search for: how to deploy" in result

    @pytest.mark.asyncio
    async def test_execute_default_query(self, tool):
        result = await tool.execute()
        assert "Simulated search for:" in result

    def test_is_tool(self, tool):
        assert isinstance(tool, ToolABC)


class TestCreateTicket:
    @pytest.fixture
    def tool(self):
        return CreateTicket()

    def test_name(self, tool):
        assert tool.name == "create_ticket"

    def test_description(self, tool):
        assert len(tool.description) > 0

    def test_input_schema(self, tool):
        schema = tool.input_schema
        assert schema["type"] == "object"
        assert "title" in schema["required"]
        assert "description" in schema["required"]
        assert "priority" not in schema["required"]

    @pytest.mark.asyncio
    async def test_create_ticket(self, tool):
        result = await tool.execute(title="Server down", description="CPU at 100%")
        assert "Ticket #1 created: Server down" in result

    @pytest.mark.asyncio
    async def test_increments_id(self, tool):
        r1 = await tool.execute(title="Issue 1", description="a")
        r2 = await tool.execute(title="Issue 2", description="b")
        assert "Ticket #1" in r1
        assert "Ticket #2" in r2

    @pytest.mark.asyncio
    async def test_priority_default(self, tool):
        await tool.execute(title="Test", description="test")
        assert tool._tickets[1]["priority"] == "medium"

    @pytest.mark.asyncio
    async def test_priority_high(self, tool):
        await tool.execute(title="Urgent", description="Critical", priority="high")
        assert tool._tickets[1]["priority"] == "high"


class TestQueryMetric:
    @pytest.fixture
    def tool(self):
        return QueryMetric()

    def test_name(self, tool):
        assert tool.name == "query_metric"

    def test_description(self, tool):
        assert len(tool.description) > 0

    def test_input_schema(self, tool):
        schema = tool.input_schema
        assert schema["type"] == "object"
        assert "metric_name" in schema["required"]
        assert list(schema["properties"]["metric_name"]["enum"]) == ["cpu", "memory", "requests_per_sec"]

    @pytest.mark.asyncio
    async def test_cpu_metric(self, tool):
        result = await tool.execute(metric_name="cpu")
        assert result.startswith("cpu:")
        assert "%" in result

    @pytest.mark.asyncio
    async def test_memory_metric(self, tool):
        result = await tool.execute(metric_name="memory")
        assert result.startswith("memory:")
        assert "%" in result

    @pytest.mark.asyncio
    async def test_requests_per_sec(self, tool):
        result = await tool.execute(metric_name="requests_per_sec")
        assert result.startswith("requests_per_sec:")

    @pytest.mark.asyncio
    async def test_unknown_metric(self, tool):
        result = await tool.execute(metric_name="disk_io")
        assert result == "disk_io: unknown"
