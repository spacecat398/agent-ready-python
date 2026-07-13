"""Explicit composition root for selected modules."""

from collections.abc import Iterator
from contextlib import contextmanager

from mixed_adapters_app.adapters.fake.text_generator import FakeTextGenerator
from mixed_adapters_app.adapters.openai_compatible_embeddings import (
    OpenAICompatibleEmbeddingProvider,
)
from mixed_adapters_app.contracts import EmbeddingProvider, TextGenerator
from mixed_adapters_app.features.documents import DocumentChunk
from mixed_adapters_app.features.embeddings import EmbeddingSettings
from mixed_adapters_app.features.retrieval import KeywordRetriever, Retriever
from mixed_adapters_app.features.retrieval.semantic import SemanticRetriever
from mixed_adapters_app.features.text_generation import TextGenerationSettings


@contextmanager
def text_generator(settings: TextGenerationSettings) -> Iterator[TextGenerator]:
    """Build exactly the Adapter selected during project generation."""
    if settings.provider != "fake":
        raise ValueError("generated project requires the fake provider")
    yield FakeTextGenerator(settings.fake_response)


@contextmanager
def embedding_provider(
    settings: EmbeddingSettings
) -> Iterator[EmbeddingProvider]:
    """Build and own the selected embedding Adapter."""
    if settings.provider != "openai_compatible":
        raise ValueError(
            "generated project requires the openai-compatible "
            "embedding provider"
        )
    with OpenAICompatibleEmbeddingProvider(settings) as provider:
        yield provider


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
