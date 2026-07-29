from __future__ import annotations

from dataclasses import dataclass

import chromadb
import httpx
from chromadb import PersistentClient

from enterpriseagent.config import settings


@dataclass
class ScoredChunk:
    text: str
    score: float
    metadata: dict


class ChromaStore:
    def __init__(self, path: str = "./data/chroma") -> None:
        self.client: PersistentClient = chromadb.PersistentClient(path)
        self.collection = self.client.get_or_create_collection(
            name="docs",
            metadata={"hnsw:space": "cosine"},
        )

    async def add(self, chunks: list[dict]) -> None:
        texts = [c["text"] for c in chunks]
        metadatas = [c.get("metadata", {}) for c in chunks]
        ids = [c["id"] for c in chunks]
        embeddings = await self._embed(texts)
        self.collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    async def similarity_search(self, query: str, k: int = 5) -> list[ScoredChunk]:
        query_embedding = await self._embed([query])
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=k,
        )
        chunks: list[ScoredChunk] = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                chunks.append(
                    ScoredChunk(
                        text=doc,
                        score=results["distances"][0][i] if results["distances"] else 0.0,
                        metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                    )
                )
        return chunks

    async def _embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/embed",
                json={"model": settings.embedding_model, "input": texts},
            )
            resp.raise_for_status()
            data = resp.json()
            return data["embeddings"]
