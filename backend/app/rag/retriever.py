"""
RAGRetriever — queries the vector store and applies MMR for diversity.
Sits between the vector store and the writer/fact-checker.
"""
from __future__ import annotations

import numpy as np
from typing import Optional

from app.rag.vector_store import VectorStore
from app.rag.embedder import GeminiEmbedder
from app.config.constants import RETRIEVAL_TOP_K


class RAGRetriever:
    """
    Retrieves relevant chunks using:
    1. Embedding-based similarity search (via ChromaDB)
    2. MMR (Maximal Marginal Relevance) for diversity
    """

    def __init__(self, vector_store: VectorStore, embedder: GeminiEmbedder):
        self.vector_store = vector_store
        self.embedder = embedder

    async def retrieve(
        self,
        query: str,
        top_k: int = RETRIEVAL_TOP_K,
        collection_name: str = "research_memory",
        use_mmr: bool = True,
        mmr_lambda: float = 0.7,
        where: Optional[dict] = None,
    ) -> list[dict]:
        """
        Retrieve relevant chunks for a query.

        Args:
            query: The search query
            top_k: Number of results to return
            collection_name: ChromaDB collection to search
            use_mmr: Use MMR for diversity (recommended)
            mmr_lambda: Trade-off between relevance (1.0) and diversity (0.0)
            where: Optional ChromaDB metadata filter
        """
        # Embed the query
        query_embedding = await self.embedder.embed_query(query)

        # Get more candidates than needed for MMR
        candidate_k = min(top_k * 3, 30)
        candidates = await self.vector_store.query(
            query_embedding=query_embedding,
            collection_name=collection_name,
            top_k=candidate_k,
            where=where,
        )

        if not candidates:
            return []

        if use_mmr and len(candidates) > top_k:
            return self._mmr_rerank(candidates, query_embedding, top_k, mmr_lambda)

        return candidates[:top_k]

    async def retrieve_multi(
        self,
        queries: list[str],
        top_k: int = RETRIEVAL_TOP_K,
        collection_name: str = "research_memory",
    ) -> list[dict]:
        """Retrieve for multiple queries and deduplicate."""
        seen_ids = set()
        all_chunks = []

        per_query_k = max(3, top_k // len(queries))

        for query in queries:
            chunks = await self.retrieve(
                query, top_k=per_query_k, collection_name=collection_name
            )
            for chunk in chunks:
                cid = chunk.get("id", chunk.get("text", "")[:50])
                if cid not in seen_ids:
                    seen_ids.add(cid)
                    all_chunks.append(chunk)

        # Sort by relevance score
        all_chunks.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        return all_chunks[:top_k]

    def _mmr_rerank(
        self,
        candidates: list[dict],
        query_embedding: list[float],
        top_k: int,
        lam: float,
    ) -> list[dict]:
        """
        Maximal Marginal Relevance reranking.
        Balances relevance to query vs diversity among selected chunks.
        """
        if not candidates:
            return []

        # Get embeddings from relevance scores as proxy (we don't store embeddings)
        # Use relevance score as similarity to query
        scores = np.array([c.get("relevance_score", 0.5) for c in candidates])

        selected_indices = []
        remaining = list(range(len(candidates)))

        # Greedy MMR selection
        for _ in range(min(top_k, len(candidates))):
            if not remaining:
                break

            if not selected_indices:
                # Pick most relevant first
                best = int(np.argmax(scores[remaining]))
                best_idx = remaining[best]
            else:
                # Compute MMR score for each remaining candidate
                mmr_scores = []
                for i in remaining:
                    rel_score = scores[i]
                    # Proxy for similarity to already-selected: penalize same source
                    selected_sources = {
                        candidates[j].get("metadata", {}).get("url", "")
                        for j in selected_indices
                    }
                    curr_source = candidates[i].get("metadata", {}).get("url", "")
                    diversity_penalty = 0.3 if curr_source in selected_sources else 0.0

                    mmr = lam * rel_score - (1 - lam) * diversity_penalty
                    mmr_scores.append(mmr)

                best = int(np.argmax(mmr_scores))
                best_idx = remaining[best]

            selected_indices.append(best_idx)
            remaining.remove(best_idx)

        return [candidates[i] for i in selected_indices]
