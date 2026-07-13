import httpx
import pytest

from agent_ready_python.adapters.openai_compatible_embeddings import (
    OpenAICompatibleEmbeddingProvider,
)
from agent_ready_python.features.embeddings import EmbeddingSettings
from agent_ready_python.foundation import ConfigurationError, ResponseFormatError


def make_settings(**overrides: object) -> EmbeddingSettings:
    values: dict[str, object] = {
        "enabled": True,
        "provider": "openai_compatible",
        "api_key": "embedding-secret",
        "max_retries": 0,
    }
    values.update(overrides)
    return EmbeddingSettings(**values)


def test_remote_embeddings_require_explicit_enablement() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = OpenAICompatibleEmbeddingProvider(
            make_settings(enabled=False),
            client=client,
        )
        with pytest.raises(ConfigurationError, match="explicitly enabled"):
            provider.embed(("private document",))

    assert calls == 0


def test_embedding_response_is_ordered_by_index() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer embedding-secret"
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [0.0, 1.0]},
                    {"index": 0, "embedding": [1.0, 0.0]},
                ]
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = OpenAICompatibleEmbeddingProvider(make_settings(), client=client)
        result = provider.embed(("first", "second"))

    assert result.vectors == ((1.0, 0.0), (0.0, 1.0))


@pytest.mark.parametrize(
    "data",
    [
        [{"index": 0, "embedding": [1.0]}],
        [
            {"index": 0, "embedding": [1.0]},
            {"index": 0, "embedding": [2.0]},
        ],
        [
            {"index": 0, "embedding": [1.0]},
            {"index": 1, "embedding": [1.0, 2.0]},
        ],
    ],
)
def test_invalid_embedding_responses_are_rejected(data: list[dict]) -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json={"data": data}))
    with httpx.Client(transport=transport) as client:
        provider = OpenAICompatibleEmbeddingProvider(make_settings(), client=client)
        with pytest.raises(ResponseFormatError):
            provider.embed(("first", "second"))


def test_non_finite_embedding_values_are_rejected() -> None:
    raw_response = b'{"data":[{"index":0,"embedding":[NaN]}]}'
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            content=raw_response,
            headers={"content-type": "application/json"},
        )
    )
    with httpx.Client(transport=transport) as client:
        provider = OpenAICompatibleEmbeddingProvider(make_settings(), client=client)
        with pytest.raises(ResponseFormatError):
            provider.embed(("text",))


def test_embedding_error_does_not_expose_key_or_response_body() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, json={"secret": "embedding-secret"})
    )
    with httpx.Client(transport=transport) as client:
        provider = OpenAICompatibleEmbeddingProvider(make_settings(), client=client)
        with pytest.raises(ResponseFormatError) as caught:
            provider.embed(("text",))

    assert "embedding-secret" not in str(caught.value)
