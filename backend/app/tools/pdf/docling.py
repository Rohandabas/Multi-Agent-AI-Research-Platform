"""
DoclingParser — PDF text + table extraction using IBM's Docling library.
Implements BasePDFTool so it can be replaced with LlamaParse/Unstructured.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from app.tools.base import BasePDFTool
from app.errors.pdf import ParseException


class DoclingParser(BasePDFTool):
    """
    Parses PDFs using Docling for high-quality text + table extraction.
    Falls back to PyMuPDF if Docling fails.
    """

    def __init__(self):
        self._converter = None

    def _get_converter(self):
        """Lazy-load Docling to avoid slow startup."""
        if self._converter is None:
            try:
                from docling.document_converter import DocumentConverter
                self._converter = DocumentConverter()
            except ImportError:
                self._converter = "fallback"
        return self._converter

    async def parse(self, pdf_path: str) -> dict:
        """
        Parse a PDF file and extract text, tables, and metadata.
        Returns: {text, tables, page_count, title, metadata}
        """
        path = Path(pdf_path)
        if not path.exists():
            raise ParseException(pdf_path, "File not found")

        # Run in thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._parse_sync, str(path))
        return result

    def _parse_sync(self, pdf_path: str) -> dict:
        """Synchronous parse — runs in thread pool."""
        converter = self._get_converter()

        if converter == "fallback":
            return self._parse_with_pymupdf(pdf_path)

        try:
            result = converter.convert(pdf_path)
            doc = result.document

            # Extract full text
            text = doc.export_to_markdown()

            # Extract tables
            tables = []
            for table in doc.tables:
                try:
                    df = table.export_to_dataframe()
                    tables.append({
                        "headers": list(df.columns),
                        "rows": df.values.tolist(),
                        "markdown": df.to_markdown(index=False),
                    })
                except Exception:
                    pass

            # Metadata
            page_count = len(doc.pages) if hasattr(doc, "pages") else 0
            title = getattr(doc, "title", None) or Path(pdf_path).stem

            return {
                "text": text,
                "tables": tables,
                "page_count": page_count,
                "title": title,
                "metadata": {
                    "filename": Path(pdf_path).name,
                    "path": pdf_path,
                },
                "source_type": "pdf",
            }

        except Exception as e:
            # Fallback to PyMuPDF
            try:
                return self._parse_with_pymupdf(pdf_path)
            except Exception as fe:
                raise ParseException(pdf_path, f"Docling failed: {e}, PyMuPDF failed: {fe}")

    def _parse_with_pymupdf(self, pdf_path: str) -> dict:
        """Fallback parser using PyMuPDF (fitz)."""
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(pdf_path)
            pages_text = []
            for page in doc:
                pages_text.append(page.get_text())

            full_text = "\n\n".join(pages_text)
            return {
                "text": full_text,
                "tables": [],
                "page_count": len(doc),
                "title": Path(pdf_path).stem,
                "metadata": {"filename": Path(pdf_path).name, "path": pdf_path},
                "source_type": "pdf",
            }
        except ImportError:
            raise ParseException(pdf_path, "Neither Docling nor PyMuPDF is available")

    async def run(self, pdf_path: str, **kwargs) -> dict:
        return await self.parse(pdf_path)
