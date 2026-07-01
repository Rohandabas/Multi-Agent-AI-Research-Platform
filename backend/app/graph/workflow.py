"""
LangGraph workflow — orchestrates all research agents.

Flow:
START → planner → parallel_gather → merge → extract → embed_and_retrieve
      → fact_check → write → generate_charts → export → evaluate → END

Parallel gather runs Search + PDF + Memory simultaneously via asyncio.gather.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

from langgraph.graph import StateGraph, END

from app.graph.state import ResearchState
from app.config.constants import AGENT_PROGRESS
from app.schemas.response import ProgressEvent


def create_research_graph(
    planner_agent,
    search_agent,
    pdf_agent,
    memory_agent,
    extractor_agent,
    fact_checker_agent,
    writer_agent,
    chart_agent,
    exporter_agent,
    evaluator_agent,
    embedder,
    vector_store,
    retriever,
    reranker,
    cost_tracker,
    job_manager,
    chunker,
):
    """
    Factory function that creates and compiles the full LangGraph research graph.
    All agents and services are injected — no global singletons.
    """

    # ─── Node functions ───────────────────────────────────────────────────────

    async def planner_node(state: ResearchState) -> dict:
        """Plan the research: generate queries, entities, sections."""
        _set_progress(state, "planner", 5)
        result = await planner_agent.run(state)
        if result.success:
            model = state.get("config").model if state.get("config") else "gemini-2.0-flash"
            cost_tracker.record_from_result(result, model=model)
            return {
                "research_plan": result.data,
                "total_cost_usd": cost_tracker.total_cost_usd,
                "progress_pct": 5,
            }
        return {"error": result.error, "failed_agents": ["planner"]}

    async def parallel_gather_node(state: ResearchState) -> dict:
        """Run Search + PDF + Memory in parallel — the fastest phase."""
        if state.get("error"):
            return {}
        _set_progress(state, "parallel_gather", 20)

        config = state.get("config")
        sources = config.sources if config else ["web", "pdfs", "memory"]

        tasks = []
        task_names = []

        if "web" in sources:
            tasks.append(search_agent.run(state))
            task_names.append("search")

        if "pdfs" in sources:
            tasks.append(pdf_agent.run(state))
            task_names.append("pdf")

        if "memory" in sources:
            tasks.append(memory_agent.run(state))
            task_names.append("memory")

        results = await asyncio.gather(*tasks, return_exceptions=True)

        updates = {"progress_pct": 35}

        for name, result in zip(task_names, results):
            if isinstance(result, Exception):
                updates.setdefault("failed_agents", []).append(name)
                continue

            model = state.get("config").model if state.get("config") else "gemini-2.0-flash"
            cost_tracker.record_from_result(result, model=model)

            if name == "search" and result.success:
                updates["search_results_raw"] = result.data
                updates["search_results"] = result.data.get("results", [])
            elif name == "pdf" and result.success:
                updates["pdf_contents"] = result.data
            elif name == "memory" and result.success:
                updates["memory_chunks"] = result.data

        updates["total_cost_usd"] = cost_tracker.total_cost_usd
        return updates

    async def merge_node(state: ResearchState) -> dict:
        """Merge all gathered content into a single text blob."""
        if state.get("error"):
            return {}
        _set_progress(state, "merge", 40)

        parts = []

        # Search results
        for r in state.get("search_results", [])[:20]:
            content = r.get("content", r.get("snippet", ""))
            if content:
                parts.append(f"[Source: {r.get('title', '')}] ({r.get('url', '')})\n{content}")

        # PDF contents
        for pdf in state.get("pdf_contents", []):
            text = pdf.get("text", "")
            if text:
                parts.append(f"[PDF: {pdf.get('title', pdf.get('url', ''))}]\n{text[:5000]}")

        # Memory chunks
        for chunk in state.get("memory_chunks", []):
            text = chunk.get("text", chunk.get("document", ""))
            if text:
                parts.append(f"[Memory]\n{text}")

        merged = "\n\n---\n\n".join(parts)
        return {"merged_content": merged, "progress_pct": 40}

    async def extract_node(state: ResearchState) -> dict:
        """Extract structured facts from merged content."""
        if state.get("error"):
            return {}
        _set_progress(state, "extract", 50)
        result = await extractor_agent.run(state)
        if result.success:
            model = state.get("config").model if state.get("config") else "gemini-2.0-flash"
            cost_tracker.record_from_result(result, model=model)
            return {
                "extracted_facts": result.data,
                "total_cost_usd": cost_tracker.total_cost_usd,
                "progress_pct": 50,
            }
        return {"extracted_facts": [], "progress_pct": 50}

    async def embed_and_retrieve_node(state: ResearchState) -> dict:
        """Embed all content chunks into ChromaDB and retrieve relevant ones."""
        if state.get("error"):
            return {}
        _set_progress(state, "embed", 60)

        job_id = state.get("job_id", "unknown")
        config = state.get("config")
        collection_name = f"job_{job_id}"

        # Chunk all content
        all_docs = []
        for r in state.get("search_results", []):
            all_docs.append({
                "text": r.get("content", r.get("snippet", "")),
                "url": r.get("url", ""),
                "title": r.get("title", ""),
                "source_type": r.get("source_type", "web"),
            })
        for pdf in state.get("pdf_contents", []):
            all_docs.append({
                "text": pdf.get("text", ""),
                "url": pdf.get("url", ""),
                "title": pdf.get("title", ""),
                "source_type": "pdf",
            })

        if not all_docs:
            return {"rag_chunks": [], "progress_pct": 60}

        chunk_size = config.chunk_size if config else 1000
        overlap = config.chunk_overlap if config else 200
        chunks = chunker.chunk_many(all_docs)

        if chunks:
            try:
                # Embed chunks
                texts = [c["text"] for c in chunks]
                embeddings = await embedder.embed_documents(texts)

                # Store in vector store
                await vector_store.add_chunks(chunks, embeddings, collection_name)

                # Also store in global memory for future sessions
                await vector_store.add_chunks(chunks[:20], embeddings[:20], "research_memory")
            except Exception as e:
                pass  # RAG failure is non-fatal

        # Retrieve relevant chunks
        query = state.get("query", "")
        top_k = config.top_k if config else 10
        try:
            retrieved = await retriever.retrieve(
                query=query,
                top_k=top_k,
                collection_name=collection_name,
            )
            reranked = await reranker.rerank_async(query, retrieved, top_k=top_k)
        except Exception:
            reranked = []

        return {"rag_chunks": reranked, "progress_pct": 65}

    async def fact_check_node(state: ResearchState) -> dict:
        """Verify extracted facts against source documents."""
        if state.get("error"):
            return {}
        _set_progress(state, "fact_checker", 70)
        result = await fact_checker_agent.run(state)
        if result.success:
            model = state.get("config").model if state.get("config") else "gemini-2.0-flash"
            cost_tracker.record_from_result(result, model=model)
            return {
                "verified_facts": result.data,
                "total_cost_usd": cost_tracker.total_cost_usd,
                "progress_pct": 70,
            }
        return {"verified_facts": {"verified": [], "rejected": []}, "progress_pct": 70}

    async def write_node(state: ResearchState) -> dict:
        """Write the full research report."""
        if state.get("error"):
            return {}
        _set_progress(state, "writer", 80)
        result = await writer_agent.run(state)
        if result.success:
            model = state.get("config").model if state.get("config") else "gemini-2.0-flash"
            cost_tracker.record_from_result(result, model=model)
            return {
                "report_markdown": result.data,
                "total_cost_usd": cost_tracker.total_cost_usd,
                "progress_pct": 80,
            }
        return {"report_markdown": "# Report Generation Failed\n\nPlease try again.", "progress_pct": 80}

    async def chart_node(state: ResearchState) -> dict:
        """Generate charts from extracted data."""
        if state.get("error"):
            return {}
        _set_progress(state, "chart_generator", 88)
        result = await chart_agent.run(state)
        chart_paths = result.data if result.success else []
        return {"chart_paths": chart_paths, "progress_pct": 88}

    async def export_node(state: ResearchState) -> dict:
        """Export report to PDF, DOCX, Markdown."""
        if state.get("error"):
            return {}
        _set_progress(state, "exporter", 93)
        result = await exporter_agent.run(state)
        export_paths = result.data if result.success else {}
        return {"export_paths": export_paths, "progress_pct": 93}

    async def evaluate_node(state: ResearchState) -> dict:
        """Evaluate report quality."""
        if state.get("error"):
            return {}
        _set_progress(state, "evaluator", 98)
        result = await evaluator_agent.run(state)
        metrics = result.data if result.success else {}
        return {
            "eval_metrics": metrics,
            "progress_pct": 100,
            "total_cost_usd": cost_tracker.total_cost_usd,
        }

    # ─── Helper ───────────────────────────────────────────────────────────────

    def _set_progress(state: ResearchState, agent: str, pct: int):
        """Update progress in state (side effect — used for logging only)."""
        pass  # State is immutable in LangGraph nodes; progress is broadcast by agents

    # ─── Build graph ──────────────────────────────────────────────────────────

    graph = StateGraph(ResearchState)

    graph.add_node("planner", planner_node)
    graph.add_node("parallel_gather", parallel_gather_node)
    graph.add_node("merge", merge_node)
    graph.add_node("extract", extract_node)
    graph.add_node("embed_and_retrieve", embed_and_retrieve_node)
    graph.add_node("fact_check", fact_check_node)
    graph.add_node("write", write_node)
    graph.add_node("generate_charts", chart_node)
    graph.add_node("export", export_node)
    graph.add_node("evaluate", evaluate_node)

    # Define edges
    graph.set_entry_point("planner")
    graph.add_edge("planner", "parallel_gather")
    graph.add_edge("parallel_gather", "merge")
    graph.add_edge("merge", "extract")
    graph.add_edge("extract", "embed_and_retrieve")
    graph.add_edge("embed_and_retrieve", "fact_check")
    graph.add_edge("fact_check", "write")
    graph.add_edge("write", "generate_charts")
    graph.add_edge("generate_charts", "export")
    graph.add_edge("export", "evaluate")
    graph.add_edge("evaluate", END)

    return graph.compile()
