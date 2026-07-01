"""
Reranker — cross-encoder reranking of retrieved chunks.
Currently uses a relevance-score-based reranker.
Future: swap in Cohere Rerank or a local cross-encoder with zero RAGRetriever changes.
"""
from __future__ import annotations

from app.config.constants import RERANK_TOP_K


class Reranker:
    """
    Post-retrieval reranker.
    Currently: simple relevance score reranking (baseline).
    Future: Cohere Rerank API or sentence-transformers cross-encoder.
    """

    def __init__(self, top_k: int = RERANK_TOP_K):
        self.top_k = top_k
        self._cohere_client = None  # Lazy-loaded if Cohere key is available

    def rerank(
        self,
        query: str,
        chunks: list[dict],
        top_k: int = None,
    ) -> list[dict]:
        """
        Rerank chunks by relevance to query.
        Returns top-k reranked chunks.
        """
        k = top_k or self.top_k
        if not chunks:
            return []

        # Score each chunk
        scored = []
        query_terms = set(query.lower().split())

        for chunk in chunks:
            text = chunk.get("text", "").lower()
            chunk_words = set(text.split())

            # Term overlap score
            overlap = len(query_terms & chunk_words) / max(len(query_terms), 1)

            # Combine with vector relevance score
            vector_score = chunk.get("relevance_score", 0.5)
            credibility = float(chunk.get("metadata", {}).get("credibility_score", "0.5") or 0.5)

            final_score = (0.5 * vector_score) + (0.3 * overlap) + (0.2 * credibility)
            scored.append((final_score, chunk))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        return [chunk for _, chunk in scored[:k]]

    async def rerank_async(
        self,
        query: str,
        chunks: list[dict],
        top_k: int = None,
    ) -> list[dict]:
        """Async wrapper for rerank (for future Cohere API integration)."""
        return self.rerank(query, chunks, top_k)
