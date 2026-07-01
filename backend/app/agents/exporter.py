"""
ExporterAgent — converts the Markdown report to HTML, PDF, and DOCX.
Pipeline: report.md → report.html → report.pdf + report.docx
"""
from __future__ import annotations

import time
from pathlib import Path
from app.agents.base import BaseAgent
from app.schemas.response import AgentResult
from app.schemas.request import ResearchConfig
from app.config.settings import settings


class ExporterAgent(BaseAgent):
    agent_name = "ExporterAgent"

    def __init__(self, config: ResearchConfig, export_service, job_manager=None):
        super().__init__(config, tools={"export": export_service}, job_manager=job_manager)

    async def _execute(self, state: dict) -> AgentResult:
        start = time.time()

        markdown = state.get("report_markdown", "")
        chart_paths = state.get("chart_paths", [])
        job_id = state.get("job_id", "unknown")

        if not markdown:
            return AgentResult(
                success=False, agent=self.agent_name,
                data={}, duration_seconds=0,
                error="No markdown report to export",
            )

        self.log_info(f"Exporting report for job {job_id}")
        self.log_info(f"Formats: {self.config.output_formats}")
        self.log_info(f"Embedding {len(chart_paths)} charts")

        result = await self.tools["export"].export_all(
            markdown=markdown,
            chart_paths=chart_paths,
            job_id=job_id,
            formats=self.config.output_formats,
        )

        self.log_info(
            f"Exported: "
            f"{'PDF ✓' if result.get('pdf') else ''} "
            f"{'DOCX ✓' if result.get('docx') else ''} "
            f"{'MD ✓' if result.get('markdown') else ''}"
        )

        return AgentResult(
            success=True,
            agent=self.agent_name,
            data=result,
            duration_seconds=time.time() - start,
        )
