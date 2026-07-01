"""
Internal data models passed between agents in the pipeline.
These are not exposed via the API — they live inside the graph state.
"""
from __future__ import annotations

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from dataclasses import dataclass, field


# ─── Source / Citation ────────────────────────────────────────────────────────
class Source(BaseModel):
    url: str
    title: str = "Untitled"
    snippet: Optional[str] = None
    source_type: str = "web"    # web | pdf | academic | sec | memory
    credibility_score: float = Field(0.5, ge=0.0, le=1.0)
    retrieved_at: Optional[str] = None
    is_pdf: bool = False
    domain: Optional[str] = None


class Citation(BaseModel):
    id: int
    source: Source
    inline_ref: str     # "[1]", "[2]", etc.
    quote: Optional[str] = None


# ─── Extracted facts ──────────────────────────────────────────────────────────
class ExtractedFact(BaseModel):
    category: str           # company | revenue | market_share | funding | product | risk | trend
    subject: str            # e.g. "NVIDIA"
    attribute: str          # e.g. "revenue"
    value: str              # e.g. "$44.9B"
    unit: Optional[str] = None
    year: Optional[str] = None
    confidence: float = Field(0.8, ge=0.0, le=1.0)
    source_url: Optional[str] = None
    verified: bool = False
    citation_id: Optional[int] = None


# ─── Chart specification ──────────────────────────────────────────────────────
class ChartSpec(BaseModel):
    chart_type: str             # bar | line | pie | scatter | area
    title: str
    labels: List[str]
    values: List[float]
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    series_name: str = "Value"
    color_scheme: str = "viridis"
    filename: Optional[str] = None  # set after generation


# ─── Research plan ────────────────────────────────────────────────────────────
class ResearchPlan(BaseModel):
    goal: str
    subtasks: List[str]
    search_queries: List[str]
    pdf_search_terms: List[str]
    key_entities: List[str]
    report_sections: List[str]
    chart_suggestions: List[ChartSpec] = []
    estimated_sources_needed: int = 10


# ─── PDF document ─────────────────────────────────────────────────────────────
class ParsedPDF(BaseModel):
    url: str
    filename: str
    text: str
    tables: List[Dict[str, Any]] = []
    page_count: int = 0
    title: Optional[str] = None
    source_type: str = "pdf"


# ─── Verified fact ─────────────────────────────────────────────────────────────
class VerifiedFact(BaseModel):
    fact: ExtractedFact
    verdict: str        # verified | rejected | uncertain
    confidence: float
    evidence: Optional[str] = None
    source_url: Optional[str] = None
