"""
PDF-related exceptions.
"""
from typing import Optional
from app.errors.base import ResearchException


class PDFException(ResearchException):
    """Raised when PDF operations fail."""
    pass


class DownloadException(PDFException):
    """Raised when a PDF cannot be downloaded."""

    def __init__(self, url: str, reason: str, status_code: Optional[int] = None):
        self.url = url
        self.status_code = status_code
        super().__init__(
            f"Failed to download PDF from {url}: {reason}",
            {"url": url, "reason": reason, "status_code": status_code},
        )


class ParseException(PDFException):
    """Raised when a PDF cannot be parsed."""

    def __init__(self, filename: str, reason: str):
        self.filename = filename
        super().__init__(
            f"Failed to parse PDF '{filename}': {reason}",
            {"filename": filename, "reason": reason},
        )


class FileTooLargeException(PDFException):
    """Raised when a PDF exceeds the maximum size limit."""

    def __init__(self, url: str, size_mb: float, limit_mb: int):
        super().__init__(
            f"PDF too large ({size_mb:.1f}MB > {limit_mb}MB limit): {url}",
            {"url": url, "size_mb": size_mb, "limit_mb": limit_mb},
        )
