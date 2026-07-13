"""Provider-independent embedding contract."""

from dataclasses import dataclass
from math import isfinite
from typing import Protocol


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    vectors: tuple[tuple[float, ...], ...]
    provider: str
    model: str

    def __post_init__(self) -> None:
        if not self.vectors:
            raise ValueError("embedding result must not be empty")
        dimensions = {len(vector) for vector in self.vectors}
        if dimensions == {0} or len(dimensions) != 1:
            raise ValueError("embedding vectors must have one non-zero dimension")
        if any(not isfinite(value) for vector in self.vectors for value in vector):
            raise ValueError("embedding vectors must contain only finite values")


class EmbeddingProvider(Protocol):
    def embed(self, texts: tuple[str, ...]) -> EmbeddingResult: ...
