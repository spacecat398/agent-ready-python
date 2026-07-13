"""Explicit composition root for selected modules."""

from collections.abc import Iterator
from contextlib import contextmanager

from retrieval_app.adapters.fake.embeddings import FakeEmbeddingProvider
from retrieval_app.contracts import EmbeddingProvider
from retrieval_app.features.documents import DocumentChunk
from retrieval_app.features.embeddings import EmbeddingSettings
from retrieval_app.features.retrieval import KeywordRetriever, Retriever
from retrieval_app.features.retrieval.semantic import SemanticRetriever


@contextmanager
def embedding_provider(
    settings: EmbeddingSettings
) -> Iterator[EmbeddingProvider]:
    """Build and own the selected embedding Adapter."""
    if settings.provider != "fake":
        raise ValueError(
            "generated project requires the fake embedding provider"
        )
    yield FakeEmbeddingProvider()


@contextmanager
def document_retriever(
    chunks: tuple[DocumentChunk, ...], settings: EmbeddingSettings
) -> Iterator[Retriever]:
    """Use keyword retrieval unless semantic mode is enabled."""
    if not settings.enabled:
        yield KeywordRetriever(chunks)
        return
    with embedding_provider(settings) as provider:
        yield SemanticRetriever(chunks, provider)
