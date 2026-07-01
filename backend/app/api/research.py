"""
FastAPI research routes.
POST /api/research — start a research job
GET  /api/reports  — list all reports
GET  /api/report/{id} — get a specific report
GET  /api/job/{job_id}/status — get job status
"""
from __future__ import annotations

import uuid
import asyncio
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.request import ResearchRequest
from app.schemas.response import JobStartResponse, ReportResponse, EvalMetricsResponse
from app.services.job_manager import job_manager
from app.services.report_service import ReportService
from app.database.session import get_db, get_session
from app.database import crud
from app.config.settings import settings

router = APIRouter(prefix="/api", tags=["research"])
_report_service = ReportService(job_manager)


@router.post("/research", response_model=JobStartResponse)
async def start_research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
):
    """
    Start a new research job.
    Returns a job_id for WebSocket connection and a report_id for retrieval.
    """
    job_id = str(uuid.uuid4())

    # Create report in DB using an independent session that closes immediately
    async with get_session() as db:
        report = await crud.create_report(
            db,
            job_id=job_id,
            query=request.query,
            depth=request.config.depth,
            sources_config=request.config.sources,
        )
        report_id = report.id

    # Register job in manager
    job_manager.create_job(job_id, report_id, request.query)

    # Start research in background
    background_tasks.add_task(
        _report_service.run_research,
        job_id=job_id,
        report_id=report_id,
        request=request,
    )

    ws_url = f"ws://localhost:{settings.PORT}/ws/{job_id}"

    return JobStartResponse(
        job_id=job_id,
        report_id=report_id,
        status="started",
        message="Research started. Connect to WebSocket for live progress.",
        websocket_url=ws_url,
    )


@router.get("/reports", response_model=list[ReportResponse])
async def list_reports(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List all reports, newest first."""
    reports = await crud.list_reports(db, limit=limit, offset=offset)
    return [_report_to_response(r) for r in reports]


@router.get("/report/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific report by ID."""
    report = await crud.get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    return _report_to_response(report)


@router.get("/job/{job_id}/status")
async def get_job_status(job_id: str):
    """Get the live status of a running job."""
    state = job_manager.get_job(job_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return state


def _report_to_response(report) -> ReportResponse:
    """Convert DB Report model to ReportResponse."""
    eval_metrics = None
    if hasattr(report, "eval_metrics") and report.eval_metrics:
        m = report.eval_metrics
        eval_metrics = EvalMetricsResponse(
            citation_coverage=m.citation_coverage,
            faithfulness=m.faithfulness,
            hallucination_risk=m.hallucination_risk,
            retrieval_quality=m.retrieval_quality,
            completeness=m.completeness,
        )

    return ReportResponse(
        id=report.id,
        job_id=report.job_id,
        query=report.query,
        status=report.status,
        depth=report.depth,
        report_markdown=report.report_markdown,
        pdf_path=report.pdf_path,
        docx_path=report.docx_path,
        markdown_path=report.markdown_path,
        chart_paths=report.chart_paths or [],
        total_tokens=report.total_tokens or 0,
        total_cost_usd=report.total_cost_usd or 0.0,
        duration_seconds=report.duration_seconds,
        sources_used=report.sources_used or [],
        eval_metrics=eval_metrics,
        created_at=report.created_at,
        completed_at=report.completed_at,
        error_message=report.error_message,
    )
