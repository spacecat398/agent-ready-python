"""Semantic retrieval built only against the embedding contract."""

from math import sqrt

from mixed_adapters_app.contracts import EmbeddingProvider
from mixed_adapters_app.features.documents import DocumentChunk

from .keyword import _validate_query
from .models import RetrievalMatch


class SemanticRetriever:
    def __init__(
        self,
        chunks: tuple[DocumentChunk, ...],
        provider: EmbeddingProvider,
    ) -> None:
        self._chunks = chunks
        self._provider = provider
        result = provider.embed(tuple(chunk.text for chunk in chunks))
        if len(result.vectors) != len(chunks):
            raise ValueError("embedding provider returned an unexpected vector count")
        self._vectors = result.vectors

    def search(self, query: str, top_k: int = 3) -> tuple[RetrievalMatch, ...]:
        _validate_query(query, top_k)
        query_result = self._provider.embed((query,))
        if len(query_result.vectors) != 1:
            raise ValueError("embedding provider returned an unexpected query vector count")
        query_vector = query_result.vectors[0]

        matches = []
        for chunk, vector in zip(self._chunks, self._vectors, strict=True):
            similarity = _cosine_similarity(query_vector, vector)
            matches.append(RetrievalMatch(chunk=chunk, score=(similarity + 1.0) / 2.0))

        matches.sort(key=lambda match: (-match.score, match.chunk.start, match.chunk.id))
        return tuple(matches[:top_k])


def _cosine_similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right):
        raise ValueError("embedding dimensions do not match")
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    similarity = sum(a * b for a, b in zip(left, right, strict=True)) / (
        left_norm * right_norm
    )
    return max(-1.0, min(1.0, similarity))
