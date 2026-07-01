"""
Shared utility functions used across the platform.
"""
from __future__ import annotations

import re
import hashlib
from urllib.parse import urlparse
from datetime import datetime


def clean_text(text: str) -> str:
    """Remove excessive whitespace and normalize text."""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\x20-\x7E\n]", "", text)
    return text.strip()


def truncate(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to max_length characters."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def extract_domain(url: str) -> str:
    """Extract the domain from a URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        return domain.replace("www.", "")
    except Exception:
        return ""


def url_to_slug(url: str) -> str:
    """Convert a URL to a filesystem-safe slug."""
    domain = extract_domain(url)
    path = urlparse(url).path
    slug = f"{domain}{path}".replace("/", "_").replace(".", "_")
    slug = re.sub(r"[^a-zA-Z0-9_-]", "", slug)
    return slug[:80]


def hash_text(text: str) -> str:
    """Generate a short SHA256 hash of text."""
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def format_cost(cost_usd: float) -> str:
    """Format a cost as a human-readable string."""
    if cost_usd < 0.001:
        return f"${cost_usd * 1000:.3f}m"
    return f"${cost_usd:.4f}"


def format_tokens(tokens: int) -> str:
    """Format token count as K/M."""
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.1f}M"
    if tokens >= 1_000:
        return f"{tokens / 1_000:.1f}K"
    return str(tokens)


def now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.utcnow().isoformat() + "Z"


def safe_float(value, default: float = 0.0) -> float:
    """Safely convert a value to float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def merge_dicts(*dicts: dict) -> dict:
    """Deep merge multiple dicts."""
    result = {}
    for d in dicts:
        for k, v in d.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = merge_dicts(result[k], v)
            else:
                result[k] = v
    return result
