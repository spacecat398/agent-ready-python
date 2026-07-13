"""Deterministic text generator with no network access."""

from mixed_adapters_app.contracts import TextGenerationRequest, TextGenerationResult


class FakeTextGenerator:
    def __init__(self, response: str = "Fake provider response") -> None:
        self._response = response
        self.requests: list[TextGenerationRequest] = []

    def generate(self, request: TextGenerationRequest) -> TextGenerationResult:
        self.requests.append(request)
        return TextGenerationResult(
            text=self._response,
            provider="fake",
            model="fake",
        )
