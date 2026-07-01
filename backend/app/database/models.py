"""
SQLAlchemy ORM models for the research platform.
Tables: Report, LLMCallLog, EvalMetrics, SearchResult
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Text, JSON, Boolean, ForeignKey,
)
from sqlalchemy.orm import DeclarativeBase, relationship


def _gen_id() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


# ─── Report ───────────────────────────────────────────────────────────────────
class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=_gen_id)
    job_id = Column(String, unique=True, index=True, nullable=False)
    query = Column(Text, nullable=False)
    status = Column(String, default="pending")  # pending | running | complete | error
    depth = Column(String, default="standard")
    sources_config = Column(JSON, default=list)  # ["web", "pdfs", "memory"]

    # Report content
    report_markdown = Column(Text, nullable=True)
    report_html = Column(Text, nullable=True)

    # File paths (relative to OUTPUTS_PATH)
    pdf_path = Column(String, nullable=True)
    docx_path = Column(String, nullable=True)
    markdown_path = Column(String, nullable=True)
    chart_paths = Column(JSON, default=list)

    # Cost / usage
    total_tokens = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0.0)
    duration_seconds = Column(Float, nullable=True)

    # Research data
    sources_used = Column(JSON, default=list)  # list of Source dicts
    extracted_facts = Column(JSON, nullable=True)
    research_plan = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Error info
    error_message = Column(Text, nullable=True)

    # Relationships
    llm_calls = relationship(
        "LLMCallLog", back_populates="report", cascade="all, delete-orphan"
    )
    eval_metrics = relationship(
        "EvalMetrics", back_populates="report", uselist=False, cascade="all, delete-orphan"
    )
    search_results = relationship(
        "SearchResult", back_populates="report", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Report id={self.id} status={self.status} query={self.query[:40]}>"


# ─── LLM Call Log ─────────────────────────────────────────────────────────────
class LLMCallLog(Base):
    __tablename__ = "llm_calls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String, ForeignKey("reports.id", ondelete="CASCADE"))
    agent = Column(String, nullable=False)
    model = Column(String, nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    duration_seconds = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow)

    report = relationship("Report", back_populates="llm_calls")


# ─── Evaluation Metrics ───────────────────────────────────────────────────────
class EvalMetrics(Base):
    __tablename__ = "eval_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String, ForeignKey("reports.id", ondelete="CASCADE"))

    citation_coverage = Column(Float, nullable=True)    # 0.0 – 1.0
    faithfulness = Column(Float, nullable=True)         # 0.0 – 1.0
    hallucination_risk = Column(Float, nullable=True)   # 0.0 – 1.0
    retrieval_quality = Column(Float, nullable=True)    # 0.0 – 1.0
    completeness = Column(Float, nullable=True)         # 0.0 – 1.0

    # Raw Gemini judge output
    eval_details = Column(JSON, nullable=True)

    report = relationship("Report", back_populates="eval_metrics")


# ─── Search Results ───────────────────────────────────────────────────────────
class SearchResult(Base):
    __tablename__ = "search_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String, ForeignKey("reports.id", ondelete="CASCADE"))
    query = Column(Text)
    url = Column(Text)
    title = Column(Text, nullable=True)
    snippet = Column(Text, nullable=True)
    source_type = Column(String, default="web")   # web | pdf | academic | sec
    credibility_score = Column(Float, default=0.5)
    is_pdf = Column(Boolean, default=False)
    retrieved_at = Column(DateTime, default=datetime.utcnow)

    report = relationship("Report", back_populates="search_results")
