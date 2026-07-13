"""Deterministic document processing."""

from hashlib import sha256

from .models import Document, DocumentChunk
from .settings import DocumentSettings


class TextChunker:
    def __init__(self, settings: DocumentSettings) -> None:
        self._settings = settings

    def split(self, document: Document) -> tuple[DocumentChunk, ...]:
        chunks: list[DocumentChunk] = []
        step = self._settings.chunk_size - self._settings.chunk_overlap

        for start in range(0, len(document.text), step):
            end = min(start + self._settings.chunk_size, len(document.text))
            text = document.text[start:end]
            if not text:
                break
            chunk_id = sha256(
                f"{document.id}:{start}:{end}:{text}".encode()
            ).hexdigest()
            chunks.append(
                DocumentChunk(
                    id=chunk_id,
                    document_id=document.id,
                    source_name=document.source_name,
                    text=text,
                    start=start,
                    end=end,
                )
            )
            if end == len(document.text):
                break

        return tuple(chunks)
