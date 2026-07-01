"""
ChromaDB vector store — stores and retrieves embedded document chunks.
Provides separate collections per job for isolation, plus a global memory collection.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings

from app.config.settings import settings as app_settings


class VectorStore:
    """
    ChromaDB-backed vector store.
    - Per-job collection for research isolation
    - Global 'research_memory' collection for cross-session memory
    """

    def __init__(self, persist_path: str = None):
        path = persist_path or app_settings.CHROMA_PATH
        Path(path).mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(
            path=path,
            settings=Settings(anonymized_telemetry=False),
        )

    # ─── Add documents ────────────────────────────────────────────────────────

    async def add_chunks(
        self,
        chunks: list[dict],
        embeddings: list[list[float]],
        collection_name: str,
    ) -> int:
        """
        Add chunks with their embeddings to a collection.
        Returns number of chunks added.
        """
        if not chunks or not embeddings:
            return 0

        collection = self._get_or_create(collection_name)

        ids = [str(uuid.uuid4()) for _ in chunks]
        texts = [c["text"] for c in chunks]
        metadatas = []

        for c in chunks:
            meta = {
                "url": c.get("source_url", ""),
                "chunk_index": str(c.get("chunk_index", 0)),
                "source_type": c.get("metadata", {}).get("source_type", "web"),
                "title": c.get("metadata", {}).get("title", ""),
            }
            # ChromaDB requires string values in metadata
            meta = {k: str(v) for k, v in meta.items() if v is not None}
            metadatas.append(meta)

        # Add in batches of 500 (ChromaDB recommendation)
        batch_size = 500
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i : i + batch_size]
            batch_embs = embeddings[i : i + batch_size]
            batch_docs = texts[i : i + batch_size]
            batch_meta = metadatas[i : i + batch_size]

            collection.add(
                ids=batch_ids,
                embeddings=batch_embs,
                documents=batch_docs,
                metadatas=batch_meta,
            )

        return len(ids)

    # ─── Query ────────────────────────────────────────────────────────────────

    async def query(
        self,
        query_embedding: list[float],
        collection_name: str,
        top_k: int = 10,
        where: Optional[dict] = None,
    ) -> list[dict]:
        """
        Query a collection by embedding similarity.
        Returns list of {text, metadata, distance, id}
        """
        try:
            collection = self._client.get_collection(collection_name)
        except Exception:
            return []  # Collection doesn't exist yet

        kwargs: dict = {
            "query_embeddings": [query_embedding],
            "n_results": min(top_k, collection.count()),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        results = collection.query(**kwargs)

        chunks = []
        for i, (doc, meta, dist) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )):
            chunks.append({
                "text": doc,
                "metadata": meta,
                "distance": dist,
                "relevance_score": 1.0 - dist,  # Convert distance to score
                "id": results["ids"][0][i],
            })

        return chunks

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _get_or_create(self, name: str):
        """Get or create a ChromaDB collection."""
        return self._client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    def collection_exists(self, name: str) -> bool:
        try:
            self._client.get_collection(name)
            return True
        except Exception:
            return False

    def delete_collection(self, name: str):
        """Delete a collection (e.g., per-job cleanup)."""
        try:
            self._client.delete_collection(name)
        except Exception:
            pass

    def list_collections(self) -> list[str]:
        return [c.name for c in self._client.list_collections()]
