"""Retrieval capability contract."""

from typing import Protocol

from .models import RetrievalMatch


class Retriever(Protocol):
    def search(self, query: str, top_k: int = 3) -> tuple[RetrievalMatch, ...]: ...
