"""Application-facing retrieval service."""

from .models import RetrievalMatch
from .ports import Retriever


class RetrievalService:
    def __init__(self, retriever: Retriever) -> None:
        self._retriever = retriever

    def search(self, query: str, top_k: int = 3) -> tuple[RetrievalMatch, ...]:
        return self._retriever.search(query, top_k)
