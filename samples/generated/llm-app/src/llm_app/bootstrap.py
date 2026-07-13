"""Explicit composition root for selected modules."""

from collections.abc import Iterator
from contextlib import contextmanager

from llm_app.adapters.fake.text_generator import FakeTextGenerator
from llm_app.contracts import TextGenerator
from llm_app.features.text_generation import TextGenerationSettings


@contextmanager
def text_generator(settings: TextGenerationSettings) -> Iterator[TextGenerator]:
    """Build exactly the Adapter selected during project generation."""
    if settings.provider != "fake":
        raise ValueError("generated project requires the fake provider")
    yield FakeTextGenerator(settings.fake_response)
