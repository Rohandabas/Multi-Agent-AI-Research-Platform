"""
Export routes — serve generated files (PDF, DOCX, Markdown).
"""
from __future__ import annotations

from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.database import crud

router = APIRouter(prefix="/api", tags=["export"])

FORMAT_MAP = {
    "pdf": ("pdf_path", "application/pdf", ".pdf"),
    "docx": ("docx_path", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx"),
    "markdown": ("markdown_path", "text/markdown", ".md"),
    "html": (None, "text/html", ".html"),
}


@router.get("/export/{report_id}/{format}")
async def download_export(
    report_id: str,
    format: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Download an exported report file.

    Formats: pdf | docx | markdown
    """
    if format not in FORMAT_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format '{format}'. Must be one of: {list(FORMAT_MAP.keys())}",
        )

    report = await crud.get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    field_name, media_type, ext = FORMAT_MAP[format]
    file_path = getattr(report, field_name, None) if field_name else None

    if not file_path or not Path(file_path).exists():
        raise HTTPException(
            status_code=404,
            detail=f"{format.upper()} export not found for report {report_id}",
        )

    filename = f"research_report_{report_id[:8]}{ext}"
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/{report_id}/chart/{chart_index}")
async def download_chart(
    report_id: str,
    chart_index: int,
    db: AsyncSession = Depends(get_db),
):
    """Download a specific chart PNG from a report."""
    report = await crud.get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    charts = report.chart_paths or []
    if chart_index >= len(charts):
        raise HTTPException(status_code=404, detail=f"Chart index {chart_index} not found")

    chart_path = charts[chart_index]
    if not Path(chart_path).exists():
        raise HTTPException(status_code=404, detail="Chart file not found")

    return FileResponse(
        path=chart_path,
        media_type="image/png",
        filename=f"chart_{chart_index + 1}.png",
    )
