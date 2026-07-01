"""
ResearchState — the central state TypedDict passed through the LangGraph pipeline.
Every node reads from and writes to this state.
"""
from __future__ import annotations

from typing import TypedDict, Optional, Any


class ResearchState(TypedDict, total=False):
    # ─── Input ────────────────────────────────────────────────────────────────
    job_id: str
    report_id: str
    query: str
    config: Any                     # ResearchConfig

    # ─── Planning output ──────────────────────────────────────────────────────
    research_plan: Any              # ResearchPlan

    # ─── Parallel gather outputs ──────────────────────────────────────────────
    search_results_raw: dict        # {results: list[dict], pdf_urls: list[str]}
    pdf_contents: list[dict]        # list of ParsedPDF dicts
    memory_chunks: list[dict]       # Chunks from ChromaDB memory

    # ─── Merge ────────────────────────────────────────────────────────────────
    merged_content: str             # All raw text combined
    search_results: list[dict]      # Flat list of search results (for fact checker)

    # ─── Extraction ───────────────────────────────────────────────────────────
    extracted_facts: list[Any]      # list[ExtractedFact]

    # ─── RAG ──────────────────────────────────────────────────────────────────
    rag_chunks: list[dict]          # Embedded + stored chunks retrieved back

    # ─── Verification ─────────────────────────────────────────────────────────
    verified_facts: dict            # {verified: list[VerifiedFact], rejected: list[VerifiedFact]}

    # ─── Report ───────────────────────────────────────────────────────────────
    report_markdown: str

    # ─── Charts ───────────────────────────────────────────────────────────────
    chart_paths: list[str]

    # ─── Export ───────────────────────────────────────────────────────────────
    export_paths: dict              # {pdf, docx, markdown, html}

    # ─── Evaluation ───────────────────────────────────────────────────────────
    eval_metrics: dict              # {citation_coverage, faithfulness, ...}

    # ─── Progress tracking ────────────────────────────────────────────────────
    progress_pct: int               # 0-100
    total_cost_usd: float

    # ─── Error ────────────────────────────────────────────────────────────────
    error: Optional[str]
    failed_agents: list[str]
