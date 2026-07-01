"""
Pydantic models for API requests.
"""
from pydantic import BaseModel, Field
from typing import Literal, List, Optional


class ResearchConfig(BaseModel):
    """Full research configuration — all knobs in one place."""

    depth: Literal["quick", "standard", "deep"] = "standard"
    temperature: float = Field(0.3, ge=0.0, le=1.0)
    search_limit: int = Field(10, ge=1, le=30, description="Max Tavily results per query")
    pdf_limit: int = Field(3, ge=0, le=10, description="Max PDFs to download and parse")
    top_k: int = Field(10, ge=1, le=20, description="RAG retrieval results")
    chunk_size: int = Field(1000, ge=100, le=4000)
    chunk_overlap: int = Field(200, ge=0, le=500)
    model: str = "gemini-2.0-flash"
    embedding_model: str = "models/text-embedding-004"
    output_formats: List[str] = Field(
        default=["pdf", "docx", "markdown"],
        description="Which formats to export",
    )
    max_retries: int = Field(3, ge=1, le=5)
    timeout_seconds: int = Field(60, ge=10, le=120)
    sources: List[str] = Field(
        default=["web", "pdfs", "memory"],
        description="Sources to use: web, pdfs, memory",
    )

    def apply_depth_presets(self) -> "ResearchConfig":
        """Override config values based on depth preset."""
        from app.config.constants import DEPTH_CONFIG
        preset = DEPTH_CONFIG.get(self.depth, {})
        return self.model_copy(update={
            "search_limit": preset.get("search_limit", self.search_limit),
            "pdf_limit": preset.get("pdf_limit", self.pdf_limit),
            "top_k": preset.get("top_k", self.top_k),
            "temperature": preset.get("temperature", self.temperature),
        })


class ResearchRequest(BaseModel):
    """Incoming research request from the user."""

    query: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="The research question or topic",
        examples=["Research the AI chip market in 2026. Compare NVIDIA, AMD, Groq, Cerebras."],
    )
    config: ResearchConfig = Field(
        default_factory=ResearchConfig,
        description="Research configuration",
    )
