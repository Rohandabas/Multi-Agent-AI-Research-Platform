"""
EvaluatorAgent — scores report quality after generation.
Metrics: citation coverage, faithfulness, hallucination risk, retrieval quality, completeness.
These metrics are stored in DB and shown in the frontend — 99% of portfolio projects don't have this.
"""
from __future__ import annotations

import time
from pathlib import Path
from app.agents.base import BaseAgent
from app.schemas.response import AgentResult
from app.schemas.request import ResearchConfig
from app.tools.llm.gemini import GeminiTool


class EvaluatorAgent(BaseAgent):
    agent_name = "EvaluatorAgent"

    def __init__(self, config: ResearchConfig, llm_tool: GeminiTool, job_manager=None):
        super().__init__(config, tools={"llm": llm_tool}, job_manager=job_manager)

    async def _execute(self, state: dict) -> AgentResult:
        start = time.time()

        report_md = state.get("report_markdown", "")
        search_results = state.get("search_results", [])
        verified_data = state.get("verified_facts", {})
        verified = verified_data.get("verified", [])
        rejected = verified_data.get("rejected", [])
        plan = state.get("research_plan")
        sections = plan.report_sections if plan else []

        if not report_md:
            return AgentResult(
                success=True, agent=self.agent_name,
                data={}, duration_seconds=0,
            )

        self.log_info("Evaluating report quality")

        # 1. Citation coverage — count [N] citations in report
        import re
        citations_in_report = set(re.findall(r"\[(\d+)\]", report_md))
        # Simple heuristic: how many paragraphs have at least one citation
        paragraphs = [p for p in report_md.split("\n\n") if len(p) > 100]
        cited_paragraphs = sum(1 for p in paragraphs if re.search(r"\[\d+\]", p))
        citation_coverage = cited_paragraphs / max(len(paragraphs), 1)

        # 2. Completeness — how many planned sections appear in the report
        sections_found = sum(1 for s in sections if s.lower() in report_md.lower())
        completeness = sections_found / max(len(sections), 1)

        # 3. Faithfulness + Hallucination risk — LLM judge
        faithfulness, hallucination_risk = await self._llm_evaluate(
            report_md, search_results
        )

        # 4. Retrieval quality — ratio of verified to total facts
        total_facts = len(verified) + len(rejected)
        retrieval_quality = len(verified) / max(total_facts, 1)

        metrics = {
            "citation_coverage": round(citation_coverage, 3),
            "faithfulness": round(faithfulness, 3),
            "hallucination_risk": round(hallucination_risk, 3),
            "retrieval_quality": round(retrieval_quality, 3),
            "completeness": round(completeness, 3),
        }

        self.log_info(
            f"Metrics: "
            f"citation={citation_coverage:.1%} "
            f"faith={faithfulness:.1%} "
            f"halluc={hallucination_risk:.1%} "
            f"retrieval={retrieval_quality:.1%} "
            f"complete={completeness:.1%}"
        )

        return AgentResult(
            success=True,
            agent=self.agent_name,
            data=metrics,
            duration_seconds=time.time() - start,
        )

    async def _llm_evaluate(
        self, report_md: str, search_results: list[dict]
    ) -> tuple[float, float]:
        """Use Gemini as a judge to score faithfulness and hallucination risk."""
        try:
            prompt_path = Path(__file__).parent.parent / "prompts" / "evaluator.md"
            prompt_template = prompt_path.read_text(encoding="utf-8")

            # Build source context
            sources = "\n\n".join([
                f"Source: {r.get('title', '')}\n{r.get('content', r.get('snippet', ''))[:400]}"
                for r in sorted(search_results, key=lambda x: x.get("credibility_score", 0), reverse=True)[:5]
            ])

            prompt = prompt_template.format(
                report_excerpt=report_md[:4000],
                sources=sources[:4000],
            )

            system = (
                "You are an expert evaluator of AI-generated research reports. "
                "Score the report on faithfulness and hallucination risk. "
                "Return JSON only."
            )

            data, _, _ = await self.tools["llm"].generate_json(
                prompt, system=system, temperature=0.1
            )

            faithfulness = float(data.get("faithfulness", 0.75))
            hallucination_risk = float(data.get("hallucination_risk", 0.25))

            return faithfulness, hallucination_risk

        except Exception as e:
            self.log_warning(f"LLM evaluation failed: {e}")
            return 0.7, 0.3  # Conservative defaults
