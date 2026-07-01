"""
ExtractorAgent — uses Gemini structured output to extract typed facts from raw text.
Outputs: list[ExtractedFact] — company data, revenues, market share, etc.
"""
from __future__ import annotations

import time
from pathlib import Path
from app.agents.base import BaseAgent
from app.schemas.response import AgentResult
from app.schemas.internal import ExtractedFact
from app.schemas.request import ResearchConfig
from app.tools.llm.gemini import GeminiTool
from app.errors.agent import ExtractionException


class ExtractorAgent(BaseAgent):
    agent_name = "ExtractorAgent"

    def __init__(self, config: ResearchConfig, llm_tool: GeminiTool, job_manager=None):
        super().__init__(config, tools={"llm": llm_tool}, job_manager=job_manager)

    async def _execute(self, state: dict) -> AgentResult:
        start = time.time()

        merged = state.get("merged_content", "")
        if not merged:
            return AgentResult(
                success=False, agent=self.agent_name, data=[],
                duration_seconds=0, error="No merged content to extract from"
            )

        plan = state.get("research_plan")
        entities = plan.key_entities if plan else []

        self.log_info(f"Extracting structured facts for entities: {entities[:5]}")

        # Chunk the merged content if too long (Gemini context limit)
        chunks = self._chunk_text(merged, max_chars=80000)
        self.log_info(f"Extracting from {len(chunks)} content chunks")

        prompt_path = Path(__file__).parent.parent / "prompts" / "extractor.md"
        prompt_template = prompt_path.read_text(encoding="utf-8")

        all_facts = []
        total_in_tok = 0
        total_out_tok = 0

        for i, chunk in enumerate(chunks):
            prompt = prompt_template.format(
                text=chunk[:40000],
                entities=", ".join(entities),
                query=state["query"],
            )

            system = (
                "You are a structured data extraction specialist. "
                "Extract specific, quantitative facts from the research text. "
                "Return only valid JSON."
            )

            try:
                data, in_tok, out_tok = await self.tools["llm"].generate_json(
                    prompt, system=system, temperature=0.1
                )
                total_in_tok += in_tok
                total_out_tok += out_tok

                facts_raw = data.get("facts", [])
                for f in facts_raw:
                    try:
                        all_facts.append(ExtractedFact(**f))
                    except Exception:
                        pass

                self.log_info(f"Chunk {i+1}/{len(chunks)}: extracted {len(facts_raw)} facts")

            except Exception as e:
                self.log_warning(f"Extraction failed for chunk {i+1}: {e}")
                continue

        self.log_info(f"Total extracted: {len(all_facts)} facts")
        cost = self.tools["llm"]._calculate_cost(total_in_tok, total_out_tok)

        return AgentResult(
            success=True,
            agent=self.agent_name,
            data=all_facts,
            duration_seconds=time.time() - start,
            tokens_used=total_in_tok + total_out_tok,
            cost_usd=cost,
        )

    def _chunk_text(self, text: str, max_chars: int = 80000) -> list[str]:
        if len(text) <= max_chars:
            return [text]
        chunks = []
        while text:
            chunks.append(text[:max_chars])
            text = text[max_chars:]
        return chunks
