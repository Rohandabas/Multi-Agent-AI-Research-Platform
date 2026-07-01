"""
PDFAgent — discovers, downloads, and parses PDFs.
Injects PDFDownloader and DoclingParser via constructor.
"""
from __future__ import annotations

import asyncio
import time
from app.agents.base import BaseAgent
from app.schemas.response import AgentResult
from app.schemas.request import ResearchConfig
from app.tools.pdf.downloader import PDFDownloader
from app.tools.pdf.docling import DoclingParser
from app.errors.pdf import PDFException


class PDFAgent(BaseAgent):
    agent_name = "PDFAgent"

    def __init__(
        self,
        config: ResearchConfig,
        downloader: PDFDownloader,
        parser: DoclingParser,
        job_manager=None,
    ):
        super().__init__(
            config,
            tools={"downloader": downloader, "parser": parser},
            job_manager=job_manager,
        )

    async def _execute(self, state: dict) -> AgentResult:
        start = time.time()

        # Collect PDF URLs from search results
        search_data = state.get("search_results_raw", {})
        pdf_urls_from_search = search_data.get("pdf_urls", [])

        plan = state.get("research_plan")
        plan_pdf_terms = plan.pdf_search_terms if plan else []

        # Use discovered URLs (up to pdf_limit)
        pdf_urls = pdf_urls_from_search[: self.config.pdf_limit]

        if not pdf_urls:
            self.log_info("No PDF URLs found in search results")
            return AgentResult(
                success=True,
                agent=self.agent_name,
                data=[],
                duration_seconds=time.time() - start,
            )

        self.log_info(f"Downloading and parsing {len(pdf_urls)} PDFs")

        # Download all PDFs in parallel
        download_tasks = [self._download_and_parse(url) for url in pdf_urls]
        results = await asyncio.gather(*download_tasks, return_exceptions=True)

        parsed_docs = []
        for r in results:
            if isinstance(r, Exception):
                self.log_warning(f"PDF failed: {r}")
                continue
            if r:
                parsed_docs.append(r)

        self.log_info(f"Successfully parsed {len(parsed_docs)} PDFs")

        return AgentResult(
            success=True,
            agent=self.agent_name,
            data=parsed_docs,
            duration_seconds=time.time() - start,
        )

    async def _download_and_parse(self, url: str) -> dict | None:
        """Download a PDF and parse it. Returns parsed dict or None on failure."""
        try:
            self.log_info(f"Downloading: {url[:60]}")
            local_path = await self.tools["downloader"].download(url)
            self.log_info(f"Parsing: {local_path}")
            parsed = await self.tools["parser"].parse(local_path)
            parsed["url"] = url
            return parsed
        except PDFException as e:
            self.log_warning(f"PDF error for {url}: {e.message}")
            return None
        except Exception as e:
            self.log_warning(f"Unexpected error for {url}: {e}")
            return None
