"""
FactCheckerAgent — verifies every extracted fact against source documents.
Uses Gemini as a judge: each claim is checked against the original sources.
Only verified facts make it into the final report.
"""
from __future__ import annotations

import time
from pathlib import Path
from app.agents.base import BaseAgent
from app.schemas.response import AgentResult
from app.schemas.internal import ExtractedFact, VerifiedFact
from app.schemas.request import ResearchConfig
from app.tools.llm.gemini import GeminiTool


class FactCheckerAgent(BaseAgent):
    agent_name = "FactCheckerAgent"

    def __init__(self, config: ResearchConfig, llm_tool: GeminiTool, job_manager=None):
        super().__init__(config, tools={"llm": llm_tool}, job_manager=job_manager)

    async def _execute(self, state: dict) -> AgentResult:
        start = time.time()

        extracted_facts: list[ExtractedFact] = state.get("extracted_facts", [])
        search_results = state.get("search_results", [])

        if not extracted_facts:
            return AgentResult(
                success=True, agent=self.agent_name,
                data={"verified": [], "rejected": []},
                duration_seconds=0,
            )

        self.log_info(f"Verifying {len(extracted_facts)} extracted facts")

        # Build source context (top credible sources)
        source_context = self._build_source_context(search_results)

        prompt_path = Path(__file__).parent.parent / "prompts" / "fact_checker.md"
        prompt_template = prompt_path.read_text(encoding="utf-8")

        verified = []
        rejected = []
        total_in = 0
        total_out = 0

        # Process facts in batches of 10
        batch_size = 10
        for i in range(0, len(extracted_facts), batch_size):
            batch = extracted_facts[i : i + batch_size]
            facts_text = "\n".join([
                f"- [{j+1}] {f.subject} | {f.attribute}: {f.value} (source: {f.source_url or 'unknown'})"
                for j, f in enumerate(batch)
            ])

            prompt = prompt_template.format(
                facts=facts_text,
                sources=source_context[:8000],
                query=state["query"],
            )

            system = (
                "You are a fact-checking agent. Verify each claim against the source documents. "
                "Be strict — only mark as verified if there's clear supporting evidence. "
                "Return JSON."
            )

            try:
                data, in_tok, out_tok = await self.tools["llm"].generate_json(
                    prompt, system=system, temperature=0.1
                )
                total_in += in_tok
                total_out += out_tok

                verdicts = data.get("verdicts", [])
                for j, fact in enumerate(batch):
                    verdict_data = verdicts[j] if j < len(verdicts) else {"verdict": "uncertain", "confidence": 0.5}
                    verdict = verdict_data.get("verdict", "uncertain")
                    confidence = float(verdict_data.get("confidence", 0.5))
                    evidence = verdict_data.get("evidence", "")

                    vf = VerifiedFact(
                        fact=fact,
                        verdict=verdict,
                        confidence=confidence,
                        evidence=evidence,
                    )

                    if verdict == "verified" and confidence >= 0.6:
                        fact.verified = True
                        verified.append(vf)
                    else:
                        rejected.append(vf)

            except Exception as e:
                self.log_warning(f"Fact check batch failed: {e}")
                # On failure, pass all facts as uncertain but include them
                for fact in batch:
                    verified.append(VerifiedFact(fact=fact, verdict="uncertain", confidence=0.5))

        self.log_info(f"Verified: {len(verified)}, Rejected: {len(rejected)}")
        cost = self.tools["llm"]._calculate_cost(total_in, total_out)

        return AgentResult(
            success=True,
            agent=self.agent_name,
            data={"verified": verified, "rejected": rejected},
            duration_seconds=time.time() - start,
            tokens_used=total_in + total_out,
            cost_usd=cost,
        )

    def _build_source_context(self, search_results: list[dict]) -> str:
        """Build a text block of top source snippets for verification context."""
        # Sort by credibility
        sorted_results = sorted(
            search_results,
            key=lambda x: x.get("credibility_score", 0),
            reverse=True,
        )[:10]

        lines = []
        for r in sorted_results:
            title = r.get("title", "Unknown")
            url = r.get("url", "")
            content = r.get("content", r.get("snippet", ""))[:500]
            lines.append(f"[Source: {title}] ({url})\n{content}\n")

        return "\n---\n".join(lines)
