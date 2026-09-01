from __future__ import annotations

import asyncio
import glob
import os
import re
from hashlib import md5

from enterpriseagent.rag.vector_store import ChromaStore

CHUNK_SIZE = 500
OVERLAP = 50


def chunk_markdown(content: str, source: str) -> list[dict]:
    chunks: list[dict] = []
    lines = content.split("\n")
    current_section = "header"
    current_lines: list[str] = []
    section_headers: list[str] = []

    i = 0
    while i < len(lines):
        line = lines[i]
        header_match = re.match(r"^(#{1,3})\s+(.+)$", line)

        if header_match:
            if current_lines:
                _flush_section(current_lines, source, current_section, section_headers, chunks)
                current_lines = []

            level = len(header_match.group(1))
            title = header_match.group(2).strip()
            section_headers = section_headers[: level - 1] + [title]
            current_section = title
            current_lines.append(line)
        else:
            current_lines.append(line)

        i += 1

    if current_lines:
        _flush_section(current_lines, source, current_section, section_headers, chunks)

    return chunks


def _flush_section(
    lines: list[str],
    source: str,
    section: str,
    section_headers: list[str],
    chunks: list[dict],
) -> None:
    text = "\n".join(lines).strip()
    if not text:
        return

    words = text.split()
    if len(words) <= CHUNK_SIZE:
        chunk_id = md5(f"{source}:{section}:0".encode()).hexdigest()[:12]
        chunks.append({
            "id": chunk_id,
            "text": text,
            "metadata": {
                "source": os.path.basename(source),
                "section": section,
                "section_path": " > ".join(section_headers) if section_headers else section,
                "chunk_index": 0,
                "total_chunks": 1,
            },
        })
        return

    paragraphs = text.split("\n\n")
    buffer: list[str] = []
    char_count = 0
    chunk_index = 0

    for para in paragraphs:
        if char_count + len(para.split()) > CHUNK_SIZE and buffer:
            _add_chunk(buffer, source, section, section_headers, chunk_index, chunks)
            overlap_text = buffer[-int(OVERLAP / 5 * 4):] if len(buffer) > OVERLAP / 5 else buffer
            buffer = list(overlap_text) if isinstance(overlap_text, list) else [overlap_text]
            char_count = sum(len(p.split()) for p in buffer)
            chunk_index += 1

        buffer.append(para)
        char_count += len(para.split())

    if buffer:
        _add_chunk(buffer, source, section, section_headers, chunk_index, chunks)


def _add_chunk(
    buffer: list[str],
    source: str,
    section: str,
    section_headers: list[str],
    chunk_index: int,
    chunks: list[dict],
) -> None:
    text = "\n\n".join(buffer).strip()
    if not text:
        return
    chunk_id = md5(f"{source}:{section}:{chunk_index}".encode()).hexdigest()[:12]
    chunks.append({
        "id": chunk_id,
        "text": text,
        "metadata": {
            "source": os.path.basename(source),
            "section": section,
            "section_path": " > ".join(section_headers) if section_headers else section,
            "chunk_index": chunk_index,
        },
    })


async def ingest_docs(docs_path: str = "data/docs") -> dict:
    store = ChromaStore()
    files = glob.glob(f"{docs_path}/**/*.md", recursive=True)
    
    ingestion_results = []
    total_chunks = 0

    for file_path in sorted(files):
        content = await asyncio.to_thread(_read_file, file_path)
        chunks = chunk_markdown(content, source=file_path)
        if chunks:
            await store.add(chunks)
            ingestion_results.append({
                "file": os.path.basename(file_path),
                "chunks": len(chunks)
            })
            total_chunks += len(chunks)
            print(f"  {os.path.basename(file_path)}: {len(chunks)} chunks")

    count = store.collection.count()
    print(f"\nDone. Total chunks indexed: {count}")
    
    return {
        "total_chunks": count,
        "files_processed": len(ingestion_results),
        "details": ingestion_results
    }


def _read_file(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    asyncio.run(ingest_docs())
