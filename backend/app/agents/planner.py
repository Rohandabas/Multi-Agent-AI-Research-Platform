"""
PlannerAgent — breaks the research query into a structured execution plan.
Uses Gemini to generate search queries, key entities, and report sections.
"""
from __future__ import annotations

import time
from pathlib import Path

from app.agents.base import BaseAgent
from app.schemas.response import AgentResult
from app.schemas.internal import ResearchPlan, ChartSpec
from app.schemas.request import ResearchConfig
from app.tools.llm.gemini import GeminiTool
from app.errors.agent import PlannerException
from app.config.constants import DEFAULT_REPORT_SECTIONS


class PlannerAgent(BaseAgent):
    agent_name = "PlannerAgent"

    def __init__(self, config: ResearchConfig, llm_tool: GeminiTool, job_manager=None):
        super().__init__(config, tools={"llm": llm_tool}, job_manager=job_manager)

    async def _execute(self, state: dict) -> AgentResult:
        start = time.time()
        query = state["query"]
        depth = self.config.depth

        self.log_info(f"Planning research for: {query[:80]}")

        # Load prompt template
        prompt_path = Path(__file__).parent.parent / "prompts" / "planner.md"
        prompt_template = prompt_path.read_text(encoding="utf-8")

        prompt = prompt_template.format(
            query=query,
            depth=depth,
            sources=", ".join(self.config.sources),
            search_limit=self.config.search_limit,
            pdf_limit=self.config.pdf_limit,
            sections=", ".join(DEFAULT_REPORT_SECTIONS),
        )

        system = (
            "You are an expert research planner. Your job is to analyze a research query "
            "and create a structured execution plan. Return only valid JSON."
        )

        data, in_tok, out_tok = await self.tools["llm"].generate_json(prompt, system=system)

        # Parse into ResearchPlan
        chart_suggestions = []
        for chart in data.get("chart_suggestions", []):
            try:
                chart_suggestions.append(ChartSpec(**chart))
            except Exception:
                pass

        plan = ResearchPlan(
            goal=data.get("goal", query),
            subtasks=data.get("subtasks", []),
            search_queries=data.get("search_queries", [query]),
            pdf_search_terms=data.get("pdf_search_terms", []),
            key_entities=data.get("key_entities", []),
            report_sections=data.get("report_sections", DEFAULT_REPORT_SECTIONS),
            chart_suggestions=chart_suggestions,
            estimated_sources_needed=data.get("estimated_sources_needed", 10),
        )

        self.log_info(f"Plan: {len(plan.search_queries)} queries, {len(plan.report_sections)} sections")

        tokens_used = in_tok + out_tok
        cost = self.tools["llm"]._calculate_cost(in_tok, out_tok)

        return AgentResult(
            success=True,
            agent=self.agent_name,
            data=plan,
            duration_seconds=time.time() - start,
            tokens_used=tokens_used,
            cost_usd=cost,
        )
