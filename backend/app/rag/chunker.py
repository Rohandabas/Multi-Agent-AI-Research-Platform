"""
Text chunker — splits long documents into overlapping chunks for embedding.
Supports character-based chunking with sentence boundary awareness.
"""
from __future__ import annotations

import re
from typing import Optional


class TextChunker:
    """
    Splits text into overlapping chunks for vector embedding.
    Tries to break at sentence boundaries to preserve semantic coherence.
    """

    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(
        self,
        text: str,
        metadata: Optional[dict] = None,
        source_url: str = "",
    ) -> list[dict]:
        """
        Split text into chunks.
        Returns list of {text, metadata, chunk_index, source_url}
        """
        text = self._clean_text(text)
        if not text:
            return []

        if len(text) <= self.chunk_size:
            return [{
                "text": text,
                "metadata": metadata or {},
                "chunk_index": 0,
                "source_url": source_url,
                "char_start": 0,
                "char_end": len(text),
            }]

        # Split into sentences first
        sentences = self._split_sentences(text)
        chunks = []
        current_chunk = []
        current_len = 0
        chunk_index = 0

        for sentence in sentences:
            sent_len = len(sentence)

            if current_len + sent_len > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = " ".join(current_chunk)
                chunks.append({
                    "text": chunk_text,
                    "metadata": metadata or {},
                    "chunk_index": chunk_index,
                    "source_url": source_url,
                })
                chunk_index += 1

                # Keep overlap — backtrack to include last N characters
                overlap_text = chunk_text[-self.overlap:]
                current_chunk = [overlap_text]
                current_len = len(overlap_text)

            current_chunk.append(sentence)
            current_len += sent_len + 1  # +1 for space

        # Final chunk
        if current_chunk:
            chunks.append({
                "text": " ".join(current_chunk),
                "metadata": metadata or {},
                "chunk_index": chunk_index,
                "source_url": source_url,
            })

        return chunks

    def chunk_many(
        self, documents: list[dict], max_chunks_per_doc: int = 50
    ) -> list[dict]:
        """
        Chunk multiple documents.
        Each doc dict: {text, url, title, source_type, ...}
        """
        all_chunks = []
        for doc in documents:
            text = doc.get("text", "")
            if not text:
                continue

            metadata = {
                "title": doc.get("title", ""),
                "url": doc.get("url", ""),
                "source_type": doc.get("source_type", "web"),
            }

            chunks = self.chunk(text, metadata=metadata, source_url=doc.get("url", ""))
            all_chunks.extend(chunks[:max_chunks_per_doc])

        return all_chunks

    def _clean_text(self, text: str) -> str:
        """Remove excessive whitespace and non-printable characters."""
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^\x20-\x7E\n]", "", text)
        return text.strip()

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences using regex."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]
