"""
PDF downloader with retry logic, size validation, and async HTTP.
"""
from __future__ import annotations

import asyncio
import tempfile
import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, unquote

import httpx

from app.config.constants import PDF_DOWNLOAD_TIMEOUT, PDF_MAX_SIZE_MB, MAX_RETRIES
from app.errors.pdf import DownloadException, FileTooLargeException


class PDFDownloader:
    """
    Downloads PDFs from URLs with:
    - Size validation (rejects >50MB)
    - Retry with exponential backoff
    - Async HTTP via httpx
    """

    def __init__(
        self,
        download_dir: str = "./outputs/downloads",
        timeout: int = PDF_DOWNLOAD_TIMEOUT,
        max_retries: int = MAX_RETRIES,
        max_size_mb: int = PDF_MAX_SIZE_MB,
    ):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_size_mb = max_size_mb

    async def download(self, url: str) -> str:
        """
        Download a PDF from URL to disk.
        Returns: local file path
        Raises: DownloadException, FileTooLargeException
        """
        filename = self._url_to_filename(url)
        dest_path = self.download_dir / filename

        # Skip if already downloaded
        if dest_path.exists():
            return str(dest_path)

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=True,
                    headers={"User-Agent": "Mozilla/5.0 (Research Bot)"},
                ) as client:
                    async with client.stream("GET", url) as response:
                        response.raise_for_status()

                        # Check content type
                        content_type = response.headers.get("content-type", "")
                        if "pdf" not in content_type and not url.lower().endswith(".pdf"):
                            raise DownloadException(url, f"Not a PDF: {content_type}")

                        # Check size from Content-Length header
                        content_length = response.headers.get("content-length")
                        if content_length:
                            size_mb = int(content_length) / (1024 * 1024)
                            if size_mb > self.max_size_mb:
                                raise FileTooLargeException(url, size_mb, self.max_size_mb)

                        # Stream to file
                        chunks = []
                        total_bytes = 0
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            total_bytes += len(chunk)
                            if total_bytes > self.max_size_mb * 1024 * 1024:
                                raise FileTooLargeException(
                                    url, total_bytes / (1024 * 1024), self.max_size_mb
                                )
                            chunks.append(chunk)

                        # Write to disk
                        with open(dest_path, "wb") as f:
                            for chunk in chunks:
                                f.write(chunk)

                return str(dest_path)

            except (DownloadException, FileTooLargeException):
                raise
            except httpx.HTTPStatusError as e:
                if attempt == self.max_retries:
                    raise DownloadException(url, f"HTTP {e.response.status_code}", e.response.status_code)
                await asyncio.sleep(2 ** attempt)
            except Exception as e:
                if attempt == self.max_retries:
                    raise DownloadException(url, str(e))
                await asyncio.sleep(2 ** attempt)

        raise DownloadException(url, "Max retries exceeded")

    def _url_to_filename(self, url: str) -> str:
        """Convert a URL to a safe local filename."""
        parsed = urlparse(url)
        path = unquote(parsed.path)
        base = Path(path).name or "document"
        # Sanitize
        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in base)
        if not safe.endswith(".pdf"):
            safe += ".pdf"
        return safe[:100]  # Limit length
