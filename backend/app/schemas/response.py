"""
Pydantic response schemas + AgentResult dataclass.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, List
from pydantic import BaseModel


# ─── AgentResult ──────────────────────────────────────────────────────────────
@dataclass
class AgentResult:
    """
    Standardised return type for every agent.
    Every agent.run() must return this.
    """
    success: bool
    agent: str
    data: Any
    duration_seconds: float
    tokens_used: int = 0
    cost_usd: float = 0.0
    retries: int = 0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "agent": self.agent,
            "duration_seconds": round(self.duration_seconds, 2),
            "tokens_used": self.tokens_used,
            "cost_usd": round(self.cost_usd, 6),
            "retries": self.retries,
            "error": self.error,
        }


# ─── WebSocket progress event ─────────────────────────────────────────────────
class ProgressEvent(BaseModel):
    event: str  # agent_start | agent_complete | agent_error | info | report_ready
    agent: Optional[str] = None
    message: str
    progress: int = 0   # 0-100
    cost_so_far: float = 0.0
    timestamp: str = ""
    data: Optional[dict] = None

    def __init__(self, **data):
        if not data.get("timestamp"):
            data["timestamp"] = datetime.utcnow().isoformat()
        super().__init__(**data)


# ─── Report response ──────────────────────────────────────────────────────────
class EvalMetricsResponse(BaseModel):
    citation_coverage: Optional[float] = None
    faithfulness: Optional[float] = None
    hallucination_risk: Optional[float] = None
    retrieval_quality: Optional[float] = None
    completeness: Optional[float] = None


class ReportResponse(BaseModel):
    id: str
    job_id: str
    query: str
    status: str
    depth: str
    report_markdown: Optional[str] = None
    pdf_path: Optional[str] = None
    docx_path: Optional[str] = None
    markdown_path: Optional[str] = None
    chart_paths: List[str] = []
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    duration_seconds: Optional[float] = None
    sources_used: List[dict] = []
    eval_metrics: Optional[EvalMetricsResponse] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class JobStartResponse(BaseModel):
    job_id: str
    report_id: str
    status: str = "started"
    message: str = "Research job started. Connect to WebSocket for live progress."
    websocket_url: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int = 0
    message: str = ""
    report_id: Optional[str] = None
