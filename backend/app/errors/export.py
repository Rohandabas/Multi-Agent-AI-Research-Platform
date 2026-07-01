"""
Export-related exceptions.
"""
from app.errors.base import ResearchException


class ExportException(ResearchException):
    """Raised when report export fails."""
    pass


class PDFExportException(ExportException):
    """Raised when HTML→PDF conversion fails."""

    def __init__(self, reason: str):
        super().__init__(f"PDF export failed: {reason}", {"reason": reason})


class DOCXExportException(ExportException):
    """Raised when Markdown→DOCX conversion fails."""

    def __init__(self, reason: str):
        super().__init__(f"DOCX export failed: {reason}", {"reason": reason})


class MarkdownExportException(ExportException):
    """Raised when Markdown export fails."""

    def __init__(self, reason: str):
        super().__init__(f"Markdown export failed: {reason}", {"reason": reason})
