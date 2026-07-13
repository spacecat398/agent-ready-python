"""Stable contracts shared across optional modules."""

from .embeddings import EmbeddingProvider, EmbeddingResult
from .text_generation import TextGenerationRequest, TextGenerationResult, TextGenerator

__all__ = [
    "EmbeddingProvider",
    "EmbeddingResult",
    "TextGenerationRequest",
    "TextGenerationResult",
    "TextGenerator",
]
