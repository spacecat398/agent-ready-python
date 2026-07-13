"""OpenAI-compatible Embeddings adapter with strict response validation."""

import time
from collections.abc import Callable

import httpx

from agent_ready_python.contracts import EmbeddingResult
from agent_ready_python.features.embeddings import EmbeddingSettings
from agent_ready_python.foundation import (
    AuthenticationError,
    ConfigurationError,
    ProviderError,
    RateLimitError,
    ResponseFormatError,
    TimeoutError,
)

_MAX_RETRY_DELAY_SECONDS = 5.0


class OpenAICompatibleEmbeddingProvider:
    def __init__(
        self,
        settings: EmbeddingSettings,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._settings = settings
        self._sleep = sleep
        self._owns_client = client is None
        self._client = client or httpx.Client(
            timeout=settings.timeout_seconds,
            follow_redirects=False,
            trust_env=False,
        )

    def embed(self, texts: tuple[str, ...]) -> EmbeddingResult:
        if not texts or any(not text.strip() for text in texts):
            raise ValueError("embedding input must contain non-empty text")
        if not self._settings.enabled:
            raise ConfigurationError("Remote embeddings are not explicitly enabled")

        headers = {"content-type": "application/json"}
        if self._settings.auth_mode == "bearer":
            if self._settings.api_key is None:
                raise ConfigurationError(
                    "AI_EMBEDDING_API_KEY is required for bearer authentication"
                )
            headers["authorization"] = (
                f"Bearer {self._settings.api_key.get_secret_value()}"
            )

        response = self._send(
            headers=headers,
            payload={"model": self._settings.model, "input": list(texts)},
        )
        return self._parse(response, expected_count=len(texts))

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "OpenAICompatibleEmbeddingProvider":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _send(self, headers: dict[str, str], payload: dict[str, object]) -> httpx.Response:
        url = f"{str(self._settings.base_url).rstrip('/')}/embeddings"
        for attempt in range(self._settings.max_retries + 1):
            try:
                response = self._client.post(url, headers=headers, json=payload)
            except (httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
                raise TimeoutError(
                    f"Embedding request timed out after {self._settings.timeout_seconds:g} seconds"
                ) from exc
            except httpx.ConnectError as exc:
                if attempt < self._settings.max_retries:
                    self._sleep(self._retry_delay(attempt, None))
                    continue
                raise ProviderError("Could not connect to the embedding provider") from exc
            except httpx.RequestError as exc:
                message = "Embedding request failed before a response was received"
                raise ProviderError(message) from exc

            if response.status_code in {401, 403}:
                raise AuthenticationError("Embedding provider rejected the credentials")
            if response.status_code == 429:
                if attempt < self._settings.max_retries:
                    self._sleep(self._retry_delay(attempt, response))
                    continue
                raise RateLimitError("Embedding rate limit remained after retries")
            if 500 <= response.status_code <= 599:
                if attempt < self._settings.max_retries:
                    self._sleep(self._retry_delay(attempt, response))
                    continue
                raise ProviderError(
                    f"Embedding provider returned server error {response.status_code} after retries"
                )
            if response.is_error:
                raise ProviderError(
                    f"Embedding provider returned HTTP {response.status_code}"
                )
            return response

        raise ProviderError("Embedding request exhausted its retry policy")

    def _parse(self, response: httpx.Response, expected_count: int) -> EmbeddingResult:
        try:
            items = response.json()["data"]
            if not isinstance(items, list):
                raise TypeError
            ordered: list[tuple[float, ...] | None] = [None] * expected_count
            for item in items:
                index = item["index"]
                raw_vector = item["embedding"]
                if (
                    not isinstance(index, int)
                    or isinstance(index, bool)
                    or not 0 <= index < expected_count
                    or ordered[index] is not None
                    or not isinstance(raw_vector, list)
                    or any(isinstance(value, bool) for value in raw_vector)
                ):
                    raise TypeError
                ordered[index] = tuple(float(value) for value in raw_vector)
            if any(vector is None for vector in ordered):
                raise TypeError
            vectors = tuple(vector for vector in ordered if vector is not None)
            return EmbeddingResult(
                vectors=vectors,
                provider="openai_compatible",
                model=self._settings.model,
            )
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ResponseFormatError(
                "Embedding response failed count, index, dimension, or value validation"
            ) from exc

    @staticmethod
    def _retry_delay(attempt: int, response: httpx.Response | None) -> float:
        if response is not None:
            retry_after = response.headers.get("retry-after")
            if retry_after:
                try:
                    return min(max(float(retry_after), 0.0), _MAX_RETRY_DELAY_SECONDS)
                except ValueError:
                    pass
        return min(0.25 * (2**attempt), _MAX_RETRY_DELAY_SECONDS)
