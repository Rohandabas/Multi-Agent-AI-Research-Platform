"""
CitationManager — Perplexity-style inline citation management.
Collects sources, deduplicates by URL, assigns sequential IDs,
and formats inline references [1], [2] and a full reference list.
"""
from __future__ import annotations

from typing import Optional
from app.schemas.internal import Source, Citation


class CitationManager:
    """
    Manages citations throughout the research pipeline.

    Usage:
        cm = CitationManager()
        id = cm.collect(source)          # Returns "[1]"
        cm.get_available_citations()     # For writer context
        cm.format_references_markdown()  # Full [1] ... [N] reference list
    """

    def __init__(self):
        self._sources: list[Source] = []
        self._url_to_id: dict[str, int] = {}
        self._citations: list[Citation] = []

    def collect(self, source: Source) -> str:
        """
        Add a source and return its inline reference string.
        Deduplicates by URL — same URL always gets same ID.
        """
        url = source.url.rstrip("/").lower()

        if url in self._url_to_id:
            cid = self._url_to_id[url]
            return f"[{cid}]"

        # New source
        cid = len(self._citations) + 1
        self._url_to_id[url] = cid

        citation = Citation(
            id=cid,
            source=source,
            inline_ref=f"[{cid}]",
        )
        self._citations.append(citation)
        self._sources.append(source)

        return f"[{cid}]"

    def get_citation_id(self, url: str) -> Optional[int]:
        """Look up a citation ID by URL. Returns None if not found."""
        return self._url_to_id.get(url.rstrip("/").lower())

    def get_available_citations(self) -> str:
        """
        Return a summary of available citations for the writer prompt.
        Format: [1] Title (url)
        """
        if not self._citations:
            return "No citations available yet."
        lines = []
        for c in self._citations[:30]:  # Cap at 30 for prompt length
            title = c.source.title or c.source.url
            lines.append(f"{c.inline_ref} {title} — {c.source.url}")
        return "\n".join(lines)

    def format_references_markdown(self) -> str:
        """
        Format the full reference list for the end of the report.
        Sorted by citation ID.
        """
        if not self._citations:
            return "*No references.*"

        lines = []
        for c in sorted(self._citations, key=lambda x: x.id):
            source = c.source
            title = source.title or source.url
            source_type = source.source_type.upper()
            credibility = f" *(credibility: {source.credibility_score:.0%})*" if source.credibility_score else ""
            lines.append(f"{c.inline_ref} **{title}** [{source_type}]  \n{source.url}{credibility}")

        return "\n\n".join(lines)

    def get_all_sources(self) -> list[Source]:
        """Return all collected sources."""
        return list(self._sources)

    def to_dict_list(self) -> list[dict]:
        """Serialize all sources to dicts for storage in DB."""
        return [
            {
                "id": c.id,
                "url": c.source.url,
                "title": c.source.title,
                "source_type": c.source.source_type,
                "credibility_score": c.source.credibility_score,
                "inline_ref": c.inline_ref,
            }
            for c in self._citations
        ]

    @property
    def count(self) -> int:
        return len(self._citations)

    def reset(self):
        """Clear all citations (for testing)."""
        self._sources.clear()
        self._url_to_id.clear()
        self._citations.clear()
