"""
All magic numbers and configuration constants live here.
Never scatter these across the codebase.
"""

# ─── Search ───────────────────────────────────────────────────────────────────
MAX_SEARCH_RESULTS = 15
MAX_PDFS = 5
PDF_DOWNLOAD_TIMEOUT = 30          # seconds
PDF_MAX_SIZE_MB = 50

# ─── RAG / Chunking ───────────────────────────────────────────────────────────
CHUNK_SIZE = 1000                  # characters
CHUNK_OVERLAP = 200
MAX_CHUNKS_PER_DOC = 50
RETRIEVAL_TOP_K = 10
RERANK_TOP_K = 5

# ─── LLM ──────────────────────────────────────────────────────────────────────
LLM_TEMPERATURE = 0.3
MAX_RETRIES = 3
REQUEST_TIMEOUT = 60               # seconds per LLM call
MAX_OUTPUT_TOKENS = 8192

# ─── Gemini Pricing (per 1M tokens) ───────────────────────────────────────────
GEMINI_FLASH_INPUT_PRICE_PER_1M = 0.075
GEMINI_FLASH_OUTPUT_PRICE_PER_1M = 0.30
EMBEDDING_PRICE_PER_1M = 0.000    # Gemini embeddings are free

# ─── Groq Llama 3.3 Pricing (per 1M tokens) ───────────────────────────────────
GROQ_LLAMA_INPUT_PRICE_PER_1M = 0.59
GROQ_LLAMA_OUTPUT_PRICE_PER_1M = 0.79

# ─── Depth presets ────────────────────────────────────────────────────────────
DEPTH_CONFIG = {
    "quick": {
        "search_limit": 5,
        "pdf_limit": 1,
        "top_k": 5,
        "temperature": 0.4,
    },
    "standard": {
        "search_limit": 10,
        "pdf_limit": 3,
        "top_k": 10,
        "temperature": 0.3,
    },
    "deep": {
        "search_limit": 20,
        "pdf_limit": 5,
        "top_k": 15,
        "temperature": 0.2,
    },
}

# ─── Output ───────────────────────────────────────────────────────────────────
OUTPUT_DIRS = [
    "reports",
    "charts",
    "markdown",
    "pdf",
    "docx",
    "downloads",
    "logs",
]

# ─── Report sections ──────────────────────────────────────────────────────────
DEFAULT_REPORT_SECTIONS = [
    "Executive Summary",
    "Industry Overview",
    "Market Trends",
    "Company Profiles",
    "Competitive Analysis",
    "SWOT Analysis",
    "Financial Data",
    "Future Outlook",
    "Risks",
    "References",
]

# ─── Agent progress weights (sum to 100) ──────────────────────────────────────
AGENT_PROGRESS = {
    "planner":         5,
    "search":         15,
    "pdf":            15,
    "memory":          5,
    "merge":           5,
    "extractor":      10,
    "embed":           5,
    "retrieve":        5,
    "fact_checker":   10,
    "writer":         15,
    "chart_generator": 5,
    "exporter":        3,
    "evaluator":       2,
}

# ─── Credibility scoring weights ──────────────────────────────────────────────
CREDIBLE_DOMAINS = [
    "bloomberg.com", "reuters.com", "ft.com", "wsj.com", "economist.com",
    "mckinsey.com", "gartner.com", "idc.com", "statista.com", "sec.gov",
    "arxiv.org", "nature.com", "sciencedirect.com", "ieee.org",
]
