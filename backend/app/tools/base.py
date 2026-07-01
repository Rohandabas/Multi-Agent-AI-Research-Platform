"""
Abstract base classes for all tools.
Agents depend on these abstractions — never on concrete implementations.
This makes providers swappable with zero agent changes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseTool(ABC):
    """Root base class for all tools."""

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    async def run(self, *args, **kwargs) -> Any:
        """Execute the tool."""
        ...


class BaseLLMTool(BaseTool):
    """
    Base for all LLM tools.
    Concrete: GeminiTool
    Future: OpenAITool, AnthropicTool
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> tuple[str, int, int]:
        """
        Returns: (text_response, input_tokens, output_tokens)
        """
        ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Returns: list of embedding vectors."""
        ...


class BaseSearchTool(BaseTool):
    """
    Base for all search providers.
    Concrete: TavilySearchTool
    Future: BraveSearchTool, GoogleSearchTool
    """

    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: int = 10,
        search_depth: str = "advanced",
        include_domains: Optional[list[str]] = None,
        exclude_domains: Optional[list[str]] = None,
    ) -> list[dict]:
        """
        Returns list of results, each with:
        {url, title, content, score, published_date}
        """
        ...

    @abstractmethod
    async def search_multi(
        self, queries: list[str], max_results_per_query: int = 5
    ) -> list[dict]:
        """Run multiple queries and merge deduplicated results."""
        ...


class BasePDFTool(BaseTool):
    """
    Base for all PDF parsers.
    Concrete: DoclingParser
    Future: LlamaParseParser, UnstructuredParser
    """

    @abstractmethod
    async def parse(self, pdf_path: str) -> dict:
        """
        Returns:
        {text, tables, page_count, title, metadata}
        """
        ...
