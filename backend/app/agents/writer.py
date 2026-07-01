"""
WriterAgent — generates a full professional research report section by section.
Uses CitationManager for Perplexity-style inline citations [1], [2], etc.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

from app.agents.base import BaseAgent
from app.schemas.response import AgentResult
from app.schemas.internal import VerifiedFact, Source
from app.schemas.request import ResearchConfig
from app.tools.llm.gemini import GeminiTool
from app.errors.agent import WriterException

if TYPE_CHECKING:
    from app.services.citation_manager import CitationManager


class WriterAgent(BaseAgent):
    agent_name = "WriterAgent"

    def __init__(
        self,
        config: ResearchConfig,
        llm_tool: GeminiTool,
        citation_manager: "CitationManager",
        job_manager=None,
    ):
        super().__init__(config, tools={"llm": llm_tool}, job_manager=job_manager)
        self.citation_manager = citation_manager

    async def _execute(self, state: dict) -> AgentResult:
        start = time.time()

        verified_data = state.get("verified_facts", {})
        verified_facts: list[VerifiedFact] = verified_data.get("verified", [])
        rag_chunks = state.get("rag_chunks", [])
        search_results = state.get("search_results", [])
        plan = state.get("research_plan")
        query = state["query"]

        sections = plan.report_sections if plan else [
            "Executive Summary", "Industry Overview", "Market Trends",
            "Company Profiles", "Competitive Analysis", "Future Outlook", "References"
        ]

        self.log_info(f"Writing report: {len(sections)} sections")

        # Register all sources with citation manager
        for r in search_results:
            url = r.get("url", "")
            if url:
                self.citation_manager.collect(Source(
                    url=url,
                    title=r.get("title", url),
                    snippet=r.get("snippet"),
                    source_type=r.get("source_type", "web"),
                    credibility_score=r.get("credibility_score", 0.5),
                ))

        # Build facts context
        facts_context = self._build_facts_context(verified_facts)
        rag_context = self._build_rag_context(rag_chunks)

        prompt_path = Path(__file__).parent.parent / "prompts" / "writer_section.md"
        prompt_template = prompt_path.read_text(encoding="utf-8")

        report_parts = []
        total_in = 0
        total_out = 0

        for section in sections:
            if section == "References":
                continue  # Added at the end

            self.log_info(f"Writing section: {section}")
            await self._broadcast("info", f"Writing: {section}", state)

            prompt = prompt_template.format(
                query=query,
                section=section,
                facts=facts_context[:5000],
                rag_context=rag_context[:5000],
                citations=self.citation_manager.get_available_citations(),
            )

            system = (
                f"You are an expert research analyst writing the '{section}' section of a professional report. "
                "Write in clear, authoritative prose. Use inline citations [1], [2] when referencing specific data. "
                "Do not make up data — only use provided facts."
            )

            try:
                text, in_tok, out_tok = await self.tools["llm"].generate(
                    prompt,
                    system=system,
                    temperature=self.config.temperature,
                    max_tokens=2000,
                )
                total_in += in_tok
                total_out += out_tok
                
                # Clean up any duplicated headers returned by LLM
                cleaned_text = text.strip()
                header_patterns = [
                    f"# {section}",
                    f"## {section}",
                    f"### {section}",
                    f"{section}\n===",
                    f"{section}\n---",
                ]
                for pattern in header_patterns:
                    if cleaned_text.lower().startswith(pattern.lower()):
                        cleaned_text = cleaned_text[len(pattern):].strip()
                        break
                        
                report_parts.append(f"## {section}\n\n{cleaned_text}\n")
            except Exception as e:
                self.log_warning(f"Failed to write section '{section}': {e}")
                report_parts.append(f"## {section}\n\n*Section generation failed: {e}*\n")

        # Add references section
        references_md = self.citation_manager.format_references_markdown()
        report_parts.append(f"## References\n\n{references_md}\n")

        full_report = f"# {query}\n\n" + "\n---\n\n".join(report_parts)

        self.log_info(f"Report generated: {len(full_report)} chars")
        cost = self.tools["llm"]._calculate_cost(total_in, total_out)

        return AgentResult(
            success=True,
            agent=self.agent_name,
            data=full_report,
            duration_seconds=time.time() - start,
            tokens_used=total_in + total_out,
            cost_usd=cost,
        )

    def _build_facts_context(self, verified_facts: list[VerifiedFact]) -> str:
        if not verified_facts:
            return "No verified facts available."
        lines = []
        for vf in verified_facts[:50]:
            f = vf.fact
            lines.append(
                f"• {f.subject} — {f.attribute}: {f.value}"
                + (f" ({f.year})" if f.year else "")
                + (f" [confidence: {vf.confidence:.0%}]")
            )
        return "\n".join(lines)

    def _build_rag_context(self, chunks: list[dict]) -> str:
        if not chunks:
            return ""
        parts = []
        for chunk in chunks[:10]:
            text = chunk.get("text", chunk.get("document", ""))
            source = chunk.get("metadata", {}).get("url", "")
            parts.append(f"{text[:500]}\n(Source: {source})")
        return "\n\n---\n\n".join(parts)
