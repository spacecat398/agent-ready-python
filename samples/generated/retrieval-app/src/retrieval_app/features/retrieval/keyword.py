"""Dependency-free local keyword retrieval."""

import re

from retrieval_app.features.documents import DocumentChunk

from .models import RetrievalMatch

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


def _tokens(text: str) -> set[str]:
    return {token.casefold() for token in _TOKEN_PATTERN.findall(text)}


class KeywordRetriever:
    def __init__(self, chunks: tuple[DocumentChunk, ...]) -> None:
        self._chunks = chunks
        self._chunk_tokens = tuple(_tokens(chunk.text) for chunk in chunks)

    def search(self, query: str, top_k: int = 3) -> tuple[RetrievalMatch, ...]:
        _validate_query(query, top_k)
        query_tokens = _tokens(query)
        if not query_tokens:
            return ()

        matches = []
        for chunk, chunk_tokens in zip(self._chunks, self._chunk_tokens, strict=True):
            overlap = query_tokens & chunk_tokens
            if overlap:
                matches.append(
                    RetrievalMatch(chunk=chunk, score=len(overlap) / len(query_tokens))
                )

        matches.sort(key=lambda match: (-match.score, match.chunk.start, match.chunk.id))
        return tuple(matches[:top_k])


def _validate_query(query: str, top_k: int) -> None:
    if not isinstance(top_k, int) or isinstance(top_k, bool) or not 1 <= top_k <= 20:
        raise ValueError("top_k must be an integer from 1 through 20")
    if not query.strip():
        raise ValueError("query must not be empty")
