from agent_ready_python.adapters.fake.text_generator import FakeTextGenerator
from agent_ready_python.contracts import TextGenerationRequest


def test_fake_generator_is_deterministic() -> None:
    generator = FakeTextGenerator("fixed")

    result = generator.generate(TextGenerationRequest(prompt="hello"))

    assert result.text == "fixed"
    assert result.provider == "fake"
    assert generator.requests == [TextGenerationRequest(prompt="hello")]
