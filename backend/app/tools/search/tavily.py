"""
TavilySearchTool — web search via Tavily API.
Implements BaseSearchTool so it can be swapped with Brave/Google with zero agent changes.
"""
from __future__ import annotations

import asyncio
from typing import Optional
from urllib.parse import urlparse

from tavily import AsyncTavilyClient

from app.tools.base import BaseSearchTool
from app.config.settings import settings
from app.config.constants import CREDIBLE_DOMAINS
from app.errors.search import RateLimitException, SearchTimeoutException, NoResultsException


class TavilySearchTool(BaseSearchTool):
    """
    Tavily-powered web search tool.
    Supports multi-query search with deduplication and credibility scoring.
    """

    def __init__(self, api_key: str = None):
        self._client = AsyncTavilyClient(api_key=api_key or settings.TAVILY_API_KEY)

    # ─── Single search ────────────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        max_results: int = 10,
        search_depth: str = "advanced",
        include_domains: Optional[list[str]] = None,
        exclude_domains: Optional[list[str]] = None,
    ) -> list[dict]:
        """
        Search Tavily and return enriched results with credibility scores.
        """
        try:
            kwargs: dict = {
                "query": query,
                "max_results": max_results,
                "search_depth": search_depth,
                "include_raw_content": True,
                "include_answer": False,
            }
            if include_domains:
                kwargs["include_domains"] = include_domains
            if exclude_domains:
                kwargs["exclude_domains"] = exclude_domains

            response = await self._client.search(**kwargs)
            results = response.get("results", [])

            # Enrich with metadata
            enriched = []
            for r in results:
                enriched.append({
                    "url": r.get("url", ""),
                    "title": r.get("title", ""),
                    "content": r.get("content", "") or r.get("raw_content", ""),
                    "snippet": r.get("content", "")[:300],
                    "score": r.get("score", 0.5),
                    "published_date": r.get("published_date"),
                    "source_type": self._classify_source(r.get("url", "")),
                    "credibility_score": self._score_credibility(r.get("url", ""), r.get("score", 0.5)),
                    "is_pdf": r.get("url", "").lower().endswith(".pdf"),
                    "query": query,
                })

            return enriched

        except Exception as e:
            err_str = str(e).lower()
            if "rate" in err_str or "429" in err_str:
                raise RateLimitException("Tavily")
            if "timeout" in err_str:
                raise SearchTimeoutException("Tavily", 30)
            raise

    # ─── Multi-query search ───────────────────────────────────────────────────

    async def search_multi(
        self,
        queries: list[str],
        max_results_per_query: int = 5,
    ) -> list[dict]:
        """
        Execute multiple queries in parallel and return deduplicated results.
        """
        tasks = [
            self.search(q, max_results=max_results_per_query)
            for q in queries
        ]
        results_per_query = await asyncio.gather(*tasks, return_exceptions=True)

        seen_urls: set[str] = set()
        all_results: list[dict] = []

        for res in results_per_query:
            if isinstance(res, Exception):
                continue
            for item in res:
                url = item.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(item)

        # Sort by credibility score
        all_results.sort(key=lambda x: x.get("credibility_score", 0), reverse=True)
        return all_results

    async def run(self, query: str, **kwargs) -> list[dict]:
        return await self.search(query, **kwargs)

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _score_credibility(self, url: str, tavily_score: float) -> float:
        """Score a URL's credibility based on domain reputation and Tavily score."""
        domain = urlparse(url).netloc.lower().replace("www.", "")
        if any(d in domain for d in CREDIBLE_DOMAINS):
            return min(1.0, 0.7 + tavily_score * 0.3)
        return max(0.1, tavily_score)

    def _classify_source(self, url: str) -> str:
        """Classify a URL as web, pdf, academic, or sec."""
        url_lower = url.lower()
        if url_lower.endswith(".pdf"):
            return "pdf"
        if "sec.gov" in url_lower:
            return "sec"
        if any(d in url_lower for d in ["arxiv.org", "nature.com", "sciencedirect.com", "ieee.org"]):
            return "academic"
        return "web"
