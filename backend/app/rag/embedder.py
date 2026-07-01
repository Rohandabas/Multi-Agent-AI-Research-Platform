"""
GeminiEmbedder — wraps GeminiTool for batch text embedding.
Uses models/text-embedding-004 (free, high quality).
"""
from __future__ import annotations

from app.tools.llm.gemini import GeminiTool


class GeminiEmbedder:
    """
    Embedding interface for the RAG pipeline.
    Wraps GeminiTool.embed() and embed_query() with caching.
    """

    def __init__(self, gemini_tool: GeminiTool):
        self._gemini = gemini_tool
        self._cache: dict[str, list[float]] = {}

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of documents. Results are cached."""
        # Check cache
        uncached_indices = []
        uncached_texts = []
        cached_results = {}

        for i, text in enumerate(texts):
            key = text[:200]  # Cache key from first 200 chars
            if key in self._cache:
                cached_results[i] = self._cache[key]
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)

        # Embed uncached texts
        new_embeddings = []
        if uncached_texts:
            new_embeddings = await self._gemini.embed(uncached_texts)

        # Store in cache and build result
        for i, (idx, emb) in enumerate(zip(uncached_indices, new_embeddings)):
            key = texts[idx][:200]
            self._cache[key] = emb
            cached_results[idx] = emb

        # Return in original order
        return [cached_results[i] for i in range(len(texts))]

    async def embed_query(self, query: str) -> list[float]:
        """Embed a query string (uses retrieval_query task type)."""
        return await self._gemini.embed_query(query)

    def get_embedding_dim(self) -> int:
        """Gemini text-embedding-004 outputs 768-dim vectors."""
        return 768
