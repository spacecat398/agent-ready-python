import httpx
import pytest

from agent_ready_python.adapters.openai_compatible import OpenAICompatibleTextGenerator
from agent_ready_python.contracts import TextGenerationRequest
from agent_ready_python.features.text_generation import TextGenerationSettings
from agent_ready_python.foundation import (
    AuthenticationError,
    ConfigurationError,
    RateLimitError,
    ResponseFormatError,
    TimeoutError,
)


def make_settings(**overrides: object) -> TextGenerationSettings:
    values: dict[str, object] = {
        "provider": "openai_compatible",
        "api_key": "top-secret-key",
        "max_retries": 0,
    }
    values.update(overrides)
    return TextGenerationSettings(**values)


def test_successful_response_is_converted_to_project_result() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer top-secret-key"
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "  answer  "}}]},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        generator = OpenAICompatibleTextGenerator(make_settings(), client=client)
        result = generator.generate(TextGenerationRequest(prompt="question"))

    assert result.text == "answer"
    assert result.provider == "openai_compatible"


def test_missing_bearer_key_fails_before_request() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        generator = OpenAICompatibleTextGenerator(
            make_settings(api_key=None),
            client=client,
        )
        with pytest.raises(ConfigurationError):
            generator.generate(TextGenerationRequest(prompt="question"))

    assert calls == 0


@pytest.mark.parametrize("status", [401, 403])
def test_authentication_errors_are_mapped(status: int) -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(status))
    with httpx.Client(transport=transport) as client:
        generator = OpenAICompatibleTextGenerator(make_settings(), client=client)
        with pytest.raises(AuthenticationError):
            generator.generate(TextGenerationRequest(prompt="question"))


def test_rate_limit_retries_are_bounded() -> None:
    calls = 0
    sleeps: list[float] = []

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(429, headers={"retry-after": "999"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        generator = OpenAICompatibleTextGenerator(
            make_settings(max_retries=1),
            client=client,
            sleep=sleeps.append,
        )
        with pytest.raises(RateLimitError):
            generator.generate(TextGenerationRequest(prompt="question"))

    assert calls == 2
    assert sleeps == [5.0]


def test_read_timeout_is_not_retried() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("late", request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        generator = OpenAICompatibleTextGenerator(
            make_settings(max_retries=2),
            client=client,
        )
        with pytest.raises(TimeoutError):
            generator.generate(TextGenerationRequest(prompt="question"))

    assert calls == 1


def test_malformed_response_is_rejected_without_raw_body() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, json={"secret": "top-secret-key"})
    )
    with httpx.Client(transport=transport) as client:
        generator = OpenAICompatibleTextGenerator(make_settings(), client=client)
        with pytest.raises(ResponseFormatError) as caught:
            generator.generate(TextGenerationRequest(prompt="question"))

    assert "top-secret-key" not in str(caught.value)
