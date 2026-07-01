"""
CRUD operations for all database models.
All functions accept an AsyncSession and return typed objects.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.database.models import Report, LLMCallLog, EvalMetrics, SearchResult


# ─── Report CRUD ─────────────────────────────────────────────────────────────

async def create_report(
    db: AsyncSession,
    *,
    job_id: str,
    query: str,
    depth: str = "standard",
    sources_config: list = None,
) -> Report:
    report = Report(
        job_id=job_id,
        query=query,
        depth=depth,
        sources_config=sources_config or ["web", "pdfs", "memory"],
        status="pending",
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)
    return report


async def get_report_by_job_id(db: AsyncSession, job_id: str) -> Optional[Report]:
    result = await db.execute(
        select(Report)
        .options(selectinload(Report.eval_metrics))
        .where(Report.job_id == job_id)
    )
    return result.scalar_one_or_none()


async def get_report_by_id(db: AsyncSession, report_id: str) -> Optional[Report]:
    result = await db.execute(
        select(Report)
        .options(selectinload(Report.eval_metrics))
        .where(Report.id == report_id)
    )
    return result.scalar_one_or_none()


async def list_reports(db: AsyncSession, limit: int = 20, offset: int = 0) -> List[Report]:
    result = await db.execute(
        select(Report)
        .options(selectinload(Report.eval_metrics))
        .order_by(desc(Report.created_at))
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def update_report_status(
    db: AsyncSession,
    job_id: str,
    status: str,
    error_message: Optional[str] = None,
) -> Optional[Report]:
    report = await get_report_by_job_id(db, job_id)
    if not report:
        return None
    report.status = status
    if error_message:
        report.error_message = error_message
    if status == "complete":
        report.completed_at = datetime.utcnow()
    await db.flush()
    return report


async def update_report_result(
    db: AsyncSession,
    job_id: str,
    *,
    report_markdown: Optional[str] = None,
    report_html: Optional[str] = None,
    pdf_path: Optional[str] = None,
    docx_path: Optional[str] = None,
    markdown_path: Optional[str] = None,
    chart_paths: Optional[list] = None,
    total_tokens: int = 0,
    total_cost_usd: float = 0.0,
    duration_seconds: Optional[float] = None,
    sources_used: Optional[list] = None,
    extracted_facts: Optional[dict] = None,
    research_plan: Optional[dict] = None,
) -> Optional[Report]:
    report = await get_report_by_job_id(db, job_id)
    if not report:
        return None

    if report_markdown is not None:
        report.report_markdown = report_markdown
    if report_html is not None:
        report.report_html = report_html
    if pdf_path is not None:
        report.pdf_path = pdf_path
    if docx_path is not None:
        report.docx_path = docx_path
    if markdown_path is not None:
        report.markdown_path = markdown_path
    if chart_paths is not None:
        report.chart_paths = chart_paths
    if total_tokens:
        report.total_tokens = total_tokens
    if total_cost_usd:
        report.total_cost_usd = total_cost_usd
    if duration_seconds is not None:
        report.duration_seconds = duration_seconds
    if sources_used is not None:
        report.sources_used = sources_used
    if extracted_facts is not None:
        report.extracted_facts = extracted_facts
    if research_plan is not None:
        report.research_plan = research_plan

    report.status = "complete"
    report.completed_at = datetime.utcnow()
    await db.flush()
    return report


# ─── LLM Call Log ─────────────────────────────────────────────────────────────

async def log_llm_call(
    db: AsyncSession,
    *,
    report_id: str,
    agent: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    duration_seconds: float = 0.0,
) -> LLMCallLog:
    log = LLMCallLog(
        report_id=report_id,
        agent=agent,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        duration_seconds=duration_seconds,
    )
    db.add(log)
    await db.flush()
    return log


# ─── Eval Metrics ─────────────────────────────────────────────────────────────

async def save_eval_metrics(
    db: AsyncSession,
    *,
    report_id: str,
    citation_coverage: Optional[float] = None,
    faithfulness: Optional[float] = None,
    hallucination_risk: Optional[float] = None,
    retrieval_quality: Optional[float] = None,
    completeness: Optional[float] = None,
    eval_details: Optional[dict] = None,
) -> EvalMetrics:
    metrics = EvalMetrics(
        report_id=report_id,
        citation_coverage=citation_coverage,
        faithfulness=faithfulness,
        hallucination_risk=hallucination_risk,
        retrieval_quality=retrieval_quality,
        completeness=completeness,
        eval_details=eval_details,
    )
    db.add(metrics)
    await db.flush()
    return metrics


# ─── Search Results ───────────────────────────────────────────────────────────

async def save_search_results(
    db: AsyncSession,
    report_id: str,
    results: list[dict],
) -> List[SearchResult]:
    saved = []
    for r in results:
        sr = SearchResult(
            report_id=report_id,
            query=r.get("query", ""),
            url=r.get("url", ""),
            title=r.get("title"),
            snippet=r.get("snippet") or r.get("content", "")[:500],
            source_type=r.get("source_type", "web"),
            credibility_score=r.get("credibility_score", 0.5),
            is_pdf=r.get("url", "").lower().endswith(".pdf"),
        )
        db.add(sr)
        saved.append(sr)
    await db.flush()
    return saved
