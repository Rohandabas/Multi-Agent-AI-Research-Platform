"""
Search-related exceptions.
"""
from typing import Optional
from app.errors.base import ResearchException


class SearchException(ResearchException):
    """Raised when search operations fail."""
    pass


class RateLimitException(SearchException):
    """Raised when a search provider rate-limits us."""

    def __init__(self, provider: str, retry_after: Optional[int] = None):
        self.provider = provider
        self.retry_after = retry_after
        details = {"provider": provider, "retry_after": retry_after}
        super().__init__(f"Rate limit exceeded for provider: {provider}", details)


class NoResultsException(SearchException):
    """Raised when a search returns zero results."""

    def __init__(self, query: str):
        self.query = query
        super().__init__(f"No results found for query: '{query}'", {"query": query})


class SearchTimeoutException(SearchException):
    """Raised when a search request times out."""

    def __init__(self, provider: str, timeout: int):
        super().__init__(
            f"Search timed out after {timeout}s for provider: {provider}",
            {"provider": provider, "timeout_seconds": timeout},
        )
