"""Explicit composition root for optional text generation."""

from collections.abc import Iterator
from contextlib import contextmanager

from agent_ready_python.adapters.fake.embeddings import FakeEmbeddingProvider
from agent_ready_python.adapters.fake.text_generator import FakeTextGenerator
from agent_ready_python.adapters.openai_compatible import OpenAICompatibleTextGenerator
from agent_ready_python.adapters.openai_compatible_embeddings import (
    OpenAICompatibleEmbeddingProvider,
)
from agent_ready_python.contracts import TextGenerator
from agent_ready_python.features.documents import DocumentChunk
from agent_ready_python.features.embeddings import EmbeddingSettings
from agent_ready_python.features.retrieval import KeywordRetriever, Retriever
from agent_ready_python.features.retrieval.semantic import SemanticRetriever
from agent_ready_python.features.text_generation import TextGenerationSettings


@contextmanager
def text_generator(settings: TextGenerationSettings) -> Iterator[TextGenerator]:
    """Build exactly one configured implementation and own its lifecycle."""

    if settings.provider == "fake":
        yield FakeTextGenerator(settings.fake_response)
        return

    with OpenAICompatibleTextGenerator(settings) as generator:
        yield generator


@contextmanager
def document_retriever(
    chunks: tuple[DocumentChunk, ...],
    settings: EmbeddingSettings,
) -> Iterator[Retriever]:
    """Use local keyword retrieval unless embeddings are explicitly enabled."""

    if not settings.enabled:
        yield KeywordRetriever(chunks)
        return

    if settings.provider == "fake":
        yield SemanticRetriever(chunks, FakeEmbeddingProvider())
        return

    with OpenAICompatibleEmbeddingProvider(settings) as provider:
        yield SemanticRetriever(chunks, provider)
