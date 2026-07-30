import shutil
import tempfile

import pytest

from enterpriseagent.agent.tools.search_docs import SearchDocs
from enterpriseagent.rag.ingestion import chunk_markdown
from enterpriseagent.rag.vector_store import ChromaStore


@pytest.fixture
def sample_markdown():
    return """# Title

Introduction paragraph.

## Section One

Content under section one.

### Subsection

Detailed content in a subsection.

## Section Two

Content under section two with more words to make sure it is long enough for testing purposes and to fill up some space in the buffer.
"""


class TestChunkMarkdown:
    def test_by_headers(self, sample_markdown):
        chunks = chunk_markdown(sample_markdown, source="test.md")
        assert len(chunks) == 4

    def test_each_chunk_has_required_keys(self, sample_markdown):
        chunks = chunk_markdown(sample_markdown, source="test.md")
        for c in chunks:
            assert "id" in c
            assert "text" in c
            assert "metadata" in c
            meta = c["metadata"]
            assert "source" in meta
            assert "section" in meta
            assert "chunk_index" in meta

    def test_section_path_tracks_nesting(self, sample_markdown):
        chunks = chunk_markdown(sample_markdown, source="test.md")
        sections = [c["metadata"]["section_path"] for c in chunks]
        assert "Title" in sections
        assert "Title > Section One" in sections
        assert "Title > Section One > Subsection" in sections
        assert "Title > Section Two" in sections

    def test_empty_content_returns_empty_list(self):
        chunks = chunk_markdown("", source="empty.md")
        assert chunks == []

    def test_no_headers_returns_one_chunk(self):
        chunks = chunk_markdown("Just a plain paragraph.\n\nAnother one.", source="plain.md")
        assert len(chunks) == 1

    def test_source_in_metadata(self, sample_markdown):
        chunks = chunk_markdown(sample_markdown, source="path/to/my-doc.md")
        for c in chunks:
            assert c["metadata"]["source"] == "my-doc.md"


class TestChromaStore:
    @pytest.fixture
    def store(self):
        tmp = tempfile.mkdtemp()
        yield ChromaStore(path=tmp)
        try:
            shutil.rmtree(tmp, ignore_errors=True)
        except PermissionError:
            pass

    @pytest.mark.asyncio
    async def test_add_and_search(self, store):
        chunks = [
            {"id": "1", "text": "El plan Pro cuesta 29 dólares al mes", "metadata": {"source": "pricing.md", "section": "Pro plan"}},
            {"id": "2", "text": "El plan Enterprise cuesta 99 dólares al mes", "metadata": {"source": "pricing.md", "section": "Enterprise plan"}},
            {"id": "3", "text": "Ollama es un servidor de modelos de lenguaje local", "metadata": {"source": "faq.md", "section": "General"}},
        ]
        await store.add(chunks)
        results = await store.similarity_search("precio plan enterprise", k=2)
        assert len(results) == 2
        assert results[0].metadata["source"] == "pricing.md"

    @pytest.mark.asyncio
    async def test_empty_search(self, store):
        results = await store.similarity_search("anything", k=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_search_returns_scored_chunks(self, store):
        chunks = [
            {"id": "a1", "text": "Python es un lenguaje de programación", "metadata": {"source": "faq.md", "section": "General"}},
        ]
        await store.add(chunks)
        results = await store.similarity_search("programación", k=1)
        assert len(results) == 1
        assert isinstance(results[0].score, float)
        assert results[0].text == "Python es un lenguaje de programación"

    @pytest.mark.asyncio
    async def test_idempotent_add(self, store):
        chunks = [
            {"id": "dup", "text": "Contenido duplicado", "metadata": {"source": "test.md", "section": "Test"}},
        ]
        await store.add(chunks)
        count1 = store.collection.count()
        await store.add(chunks)
        count2 = store.collection.count()
        assert count2 == count1


class TestSearchDocsRAG:
    @pytest.fixture
    def tool(self):
        tmp = tempfile.mkdtemp()
        store = ChromaStore(path=tmp)
        tool = SearchDocs(store=store)
        import asyncio
        asyncio.run(store.add([
            {"id": "p1", "text": "El plan Pro cuesta 29 dólares al mes con 100 GB de ancho de banda", "metadata": {"source": "pricing.md", "section": "Pro plan"}},
            {"id": "p2", "text": "El SLA del plan Enterprise es 99.99% de disponibilidad mensual", "metadata": {"source": "slas.md", "section": "Enterprise SLA"}},
            {"id": "p3", "text": "Para desplegar una app usa el comando nimbus deploy", "metadata": {"source": "getting-started.md", "section": "Deploy"}},
        ]))
        yield tool
        try:
            shutil.rmtree(tmp, ignore_errors=True)
        except PermissionError:
            pass

    @pytest.mark.asyncio
    async def test_formats_sources_with_brackets(self, tool):
        result = await tool.execute(query="precios planes")
        assert "[1]" in result
        assert "pricing.md" in result
        assert "dólares" in result

    @pytest.mark.asyncio
    async def test_returns_multiple_sources(self, tool):
        result = await tool.execute(query="SLA enterprise")
        assert "[1]" in result
        assert "99.99%" in result or "99.99" in result

    @pytest.mark.asyncio
    async def test_no_results_message(self, tool):
        result = await tool.execute(query="zzzzzzzzzzzzzzzzzzzzzzzzz")
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_each_source_line_has_section(self, tool):
        result = await tool.execute(query="deploy app")
        lines = result.split("\n")
        for line in lines:
            if line.strip() and line.startswith("["):
                assert ">" in line

    @pytest.mark.asyncio
    async def test_respects_k_limit(self, tool):
        result = await tool.execute(query="plan")
        assert result.count("[") <= 5
