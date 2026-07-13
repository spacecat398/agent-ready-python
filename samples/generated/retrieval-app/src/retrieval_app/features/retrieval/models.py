"""Stable retrieval result types."""

from dataclasses import dataclass

from retrieval_app.features.documents import DocumentChunk


@dataclass(frozen=True, slots=True)
class RetrievalMatch:
    chunk: DocumentChunk
    score: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("retrieval score must be between 0 and 1")
