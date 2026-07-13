"""Interface-independent application services."""

from mixed_adapters_app.contracts import (
    TextGenerationRequest,
    TextGenerationResult,
    TextGenerator,
)


class AskService:
    def __init__(self, generator: TextGenerator) -> None:
        self._generator = generator

    def ask(self, prompt: str) -> TextGenerationResult:
        return self._generator.generate(TextGenerationRequest(prompt=prompt))
