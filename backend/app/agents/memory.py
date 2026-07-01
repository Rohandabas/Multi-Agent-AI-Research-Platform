"""
MemoryAgent — retrieves relevant prior knowledge from ChromaDB.
Enables cross-session knowledge reuse: "compare with last month's report."
"""
from __future__ import annotations

import time
from app.agents.base import BaseAgent
from app.schemas.response import AgentResult
from app.schemas.request import ResearchConfig


class MemoryAgent(BaseAgent):
    agent_name = "MemoryAgent"

    def __init__(self, config: ResearchConfig, retriever, job_manager=None):
        """
        Args:
            retriever: RAG retriever (app.rag.retriever.RAGRetriever)
        """
        super().__init__(config, tools={"retriever": retriever}, job_manager=job_manager)

    async def _execute(self, state: dict) -> AgentResult:
        start = time.time()
        query = state["query"]

        plan = state.get("research_plan")
        key_entities = plan.key_entities if plan else []

        # Build retrieval queries from the plan
        retrieval_queries = [query] + [
            f"{entity} research data" for entity in key_entities[:5]
        ]

        self.log_info(f"Retrieving prior knowledge for {len(retrieval_queries)} queries")

        all_chunks = []
        for q in retrieval_queries:
            try:
                chunks = await self.tools["retriever"].retrieve(
                    query=q,
                    top_k=self.config.top_k // len(retrieval_queries),
                    collection_name="research_memory",
                )
                all_chunks.extend(chunks)
            except Exception as e:
                self.log_warning(f"Memory retrieval failed for '{q}': {e}")
                continue

        # Deduplicate by chunk id
        seen = set()
        unique_chunks = []
        for chunk in all_chunks:
            cid = chunk.get("id", chunk.get("text", "")[:50])
            if cid not in seen:
                seen.add(cid)
                unique_chunks.append(chunk)

        self.log_info(f"Retrieved {len(unique_chunks)} unique memory chunks")

        return AgentResult(
            success=True,
            agent=self.agent_name,
            data=unique_chunks,
            duration_seconds=time.time() - start,
        )
