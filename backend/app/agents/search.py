"""
SearchAgent — executes web searches via the injected search tool.
Runs all planned queries in parallel and ranks by credibility.
"""
from __future__ import annotations

import time
from app.agents.base import BaseAgent
from app.schemas.response import AgentResult
from app.schemas.request import ResearchConfig
from app.tools.search.tavily import TavilySearchTool
from app.errors.search import SearchException


class SearchAgent(BaseAgent):
    agent_name = "SearchAgent"

    def __init__(
        self,
        config: ResearchConfig,
        search_tool: TavilySearchTool,
        job_manager=None,
    ):
        super().__init__(config, tools={"search": search_tool}, job_manager=job_manager)

    async def _execute(self, state: dict) -> AgentResult:
        start = time.time()

        plan = state.get("research_plan")
        if not plan:
            return AgentResult(
                success=False, agent=self.agent_name, data=[],
                duration_seconds=0, error="No research plan found"
            )

        queries = plan.search_queries[: self.config.search_limit]
        self.log_info(f"Running {len(queries)} search queries in parallel")

        try:
            results = await self.tools["search"].search_multi(
                queries,
                max_results_per_query=max(3, self.config.search_limit // len(queries)),
            )
        except SearchException as e:
            self.log_error(f"Search failed: {e.message}")
            results = []

        # Identify PDFs in results for later download
        pdf_urls = [
            r["url"] for r in results
            if r.get("is_pdf") or r.get("url", "").lower().endswith(".pdf")
        ]

        self.log_info(f"Found {len(results)} results ({len(pdf_urls)} PDFs)")

        return AgentResult(
            success=True,
            agent=self.agent_name,
            data={"results": results, "pdf_urls": pdf_urls},
            duration_seconds=time.time() - start,
        )
