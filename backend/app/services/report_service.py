"""
ReportService — orchestrates the full research pipeline.
Creates all agents with proper DI, runs the LangGraph graph,
persists results to DB, and broadcasts final status via WebSocket.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime

from app.graph.workflow import create_research_graph
from app.graph.state import ResearchState
from app.schemas.request import ResearchRequest, ResearchConfig
from app.schemas.response import ProgressEvent
from app.services.job_manager import JobManager
from app.services.citation_manager import CitationManager
from app.services.cost_tracker import CostTracker
from app.services.export_service import ExportService
from app.database.session import get_session
from app.database import crud
from app.config.constants import DEPTH_CONFIG

# Agents
from app.agents.planner import PlannerAgent
from app.agents.search import SearchAgent
from app.agents.pdf_agent import PDFAgent
from app.agents.memory import MemoryAgent
from app.agents.extractor import ExtractorAgent
from app.agents.fact_checker import FactCheckerAgent
from app.agents.writer import WriterAgent
from app.agents.chart_generator import ChartGeneratorAgent
from app.agents.exporter import ExporterAgent
from app.agents.evaluator import EvaluatorAgent

# Tools
from app.config.settings import settings
from app.tools.llm.gemini import GeminiTool
from app.tools.llm.groq import GroqTool
from app.tools.search.tavily import TavilySearchTool
from app.tools.pdf.downloader import PDFDownloader
from app.tools.pdf.docling import DoclingParser

# RAG
from app.rag.chunker import TextChunker
from app.rag.embedder import GeminiEmbedder
from app.rag.vector_store import VectorStore
from app.rag.retriever import RAGRetriever
from app.rag.reranker import Reranker

from app.logging.logger import AgentLogger


class ReportService:
    """
    Top-level orchestrator for the research pipeline.
    Run as a background asyncio task.
    """

    def __init__(self, job_manager: JobManager):
        self.job_manager = job_manager

    async def run_research(
        self,
        job_id: str,
        report_id: str,
        request: ResearchRequest,
    ):
        """
        Full pipeline execution. Called as a background task.
        """
        logger = AgentLogger("ReportService", job_id)
        logger.started(f"Query: {request.query[:80]}")
        start_time = time.time()

        # Apply depth presets to config
        config = request.config.apply_depth_presets()

        # ── Initialize all tools ──────────────────────────────────────────────
        provider = settings.LLM_PROVIDER
        model_name = config.model
        if model_name == "gemini-2.0-flash":
            model_name = "gemini-2.0-flash-lite"
        model_lower = model_name.lower()
        if "llama" in model_lower or "mixtral" in model_lower or "groq" in model_lower:
            provider = "groq"

        gemini_llm = GeminiTool(model=model_name, embedding_model=config.embedding_model)

        if provider == "groq":
            if "gemini" in model_lower or "models/" in model_lower:
                model_name = settings.GROQ_MODEL
            llm_tool = GroqTool(model=model_name)
        else:
            llm_tool = gemini_llm

        search_tool = TavilySearchTool()
        pdf_downloader = PDFDownloader()
        pdf_parser = DoclingParser()

        # ── Initialize RAG ────────────────────────────────────────────────────
        vector_store = VectorStore()
        embedder = GeminiEmbedder(gemini_llm)
        retriever = RAGRetriever(vector_store, embedder)
        reranker = Reranker(top_k=config.top_k)
        chunker = TextChunker(chunk_size=config.chunk_size, overlap=config.chunk_overlap)

        # ── Initialize services ───────────────────────────────────────────────
        citation_manager = CitationManager()
        cost_tracker = CostTracker()
        export_service = ExportService()

        # ── Wire up all agents with DI ────────────────────────────────────────
        planner = PlannerAgent(config, llm_tool, self.job_manager)
        search = SearchAgent(config, search_tool, self.job_manager)
        pdf = PDFAgent(config, pdf_downloader, pdf_parser, self.job_manager)
        memory = MemoryAgent(config, retriever, self.job_manager)
        extractor = ExtractorAgent(config, llm_tool, self.job_manager)
        fact_checker = FactCheckerAgent(config, llm_tool, self.job_manager)
        writer = WriterAgent(config, llm_tool, citation_manager, self.job_manager)
        chart_gen = ChartGeneratorAgent(config, self.job_manager)
        exporter = ExporterAgent(config, export_service, self.job_manager)
        evaluator = EvaluatorAgent(config, llm_tool, self.job_manager)

        # ── Build the LangGraph ───────────────────────────────────────────────
        graph = create_research_graph(
            planner_agent=planner,
            search_agent=search,
            pdf_agent=pdf,
            memory_agent=memory,
            extractor_agent=extractor,
            fact_checker_agent=fact_checker,
            writer_agent=writer,
            chart_agent=chart_gen,
            exporter_agent=exporter,
            evaluator_agent=evaluator,
            embedder=embedder,
            vector_store=vector_store,
            retriever=retriever,
            reranker=reranker,
            cost_tracker=cost_tracker,
            job_manager=self.job_manager,
            chunker=chunker,
        )

        # ── Initial state ─────────────────────────────────────────────────────
        initial_state: ResearchState = {
            "job_id": job_id,
            "report_id": report_id,
            "query": request.query,
            "config": config,
            "progress_pct": 0,
            "total_cost_usd": 0.0,
            "failed_agents": [],
        }

        try:
            # Update DB status → running
            async with get_session() as db:
                await crud.update_report_status(db, job_id, "running")

            # ── Run the graph ─────────────────────────────────────────────────
            logger.info("Starting LangGraph pipeline")
            final_state = await graph.ainvoke(initial_state)
            if final_state.get("error"):
                raise RuntimeError(f"Graph execution failed: {final_state.get('error')}")
            duration = time.time() - start_time

            # ── Extract results ───────────────────────────────────────────────
            export_paths = final_state.get("export_paths", {})
            chart_paths = final_state.get("chart_paths", [])
            sources_used = citation_manager.to_dict_list()
            cost_summary = cost_tracker.get_summary()
            eval_metrics = final_state.get("eval_metrics", {})

            # ── Persist to DB ──────────────────────────────────────────────────
            async with get_session() as db:
                await crud.update_report_result(
                    db,
                    job_id=job_id,
                    report_markdown=final_state.get("report_markdown", ""),
                    pdf_path=export_paths.get("pdf"),
                    docx_path=export_paths.get("docx"),
                    markdown_path=export_paths.get("markdown"),
                    chart_paths=chart_paths,
                    total_tokens=cost_summary["total_tokens"],
                    total_cost_usd=cost_summary["total_cost_usd"],
                    duration_seconds=duration,
                    sources_used=sources_used,
                    extracted_facts={
                        "count": len(final_state.get("extracted_facts", [])),
                        "verified": len(final_state.get("verified_facts", {}).get("verified", [])),
                    },
                    research_plan=final_state.get("research_plan", {}).model_dump()
                        if hasattr(final_state.get("research_plan"), "model_dump") else None,
                )

                # Save eval metrics
                if eval_metrics:
                    await crud.save_eval_metrics(
                        db,
                        report_id=report_id,
                        **eval_metrics,
                    )

                # Save search results
                search_results = final_state.get("search_results", [])
                if search_results:
                    await crud.save_search_results(db, report_id, search_results)

            # ── Mark complete and broadcast ────────────────────────────────────
            self.job_manager.complete_job(job_id)

            await self.job_manager.broadcast(job_id, ProgressEvent(
                event="report_ready",
                message="Research complete! Your report is ready.",
                progress=100,
                cost_so_far=cost_summary["total_cost_usd"],
                data={
                    "report_id": report_id,
                    "pdf_path": export_paths.get("pdf"),
                    "cost_summary": cost_summary,
                    "eval_metrics": eval_metrics,
                },
            ))

            logger.finished(
                tokens_input=cost_summary["total_input_tokens"],
                tokens_output=cost_summary["total_output_tokens"],
                cost_usd=cost_summary["total_cost_usd"],
            )

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", e)

            async with get_session() as db:
                await crud.update_report_status(db, job_id, "error", str(e))

            self.job_manager.fail_job(job_id, str(e))

            await self.job_manager.broadcast(job_id, ProgressEvent(
                event="agent_error",
                message=f"Research failed: {str(e)}",
                progress=0,
                cost_so_far=cost_tracker.total_cost_usd,
            ))
