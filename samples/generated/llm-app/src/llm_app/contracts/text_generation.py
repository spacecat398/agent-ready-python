"""Provider-independent text generation contract."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class TextGenerationRequest:
    prompt: str
    system: str | None = None

    def __post_init__(self) -> None:
        if not self.prompt.strip():
            raise ValueError("prompt must not be empty")


@dataclass(frozen=True, slots=True)
class TextGenerationResult:
    text: str
    provider: str
    model: str

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("generated text must not be empty")


class TextGenerator(Protocol):
    def generate(self, request: TextGenerationRequest) -> TextGenerationResult: ...
