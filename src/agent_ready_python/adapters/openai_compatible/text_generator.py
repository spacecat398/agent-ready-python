"""Thin OpenAI-compatible Chat Completions adapter."""

import time
from collections.abc import Callable

import httpx

from agent_ready_python.contracts import (
    TextGenerationRequest,
    TextGenerationResult,
)
from agent_ready_python.features.text_generation import TextGenerationSettings
from agent_ready_python.foundation import (
    AuthenticationError,
    ConfigurationError,
    ProviderError,
    RateLimitError,
    ResponseFormatError,
    TimeoutError,
)

_MAX_RETRY_DELAY_SECONDS = 5.0


class OpenAICompatibleTextGenerator:
    def __init__(
        self,
        settings: TextGenerationSettings,
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

    def generate(self, request: TextGenerationRequest) -> TextGenerationResult:
        headers = {"content-type": "application/json"}
        if self._settings.auth_mode == "bearer":
            if self._settings.api_key is None:
                raise ConfigurationError("AI_LLM_API_KEY is required for bearer authentication")
            headers["authorization"] = (
                f"Bearer {self._settings.api_key.get_secret_value()}"
            )

        messages: list[dict[str, str]] = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.append({"role": "user", "content": request.prompt})

        response = self._send(
            headers=headers,
            payload={"model": self._settings.model, "messages": messages},
        )
        return self._parse(response)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "OpenAICompatibleTextGenerator":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _send(self, headers: dict[str, str], payload: dict[str, object]) -> httpx.Response:
        url = f"{str(self._settings.base_url).rstrip('/')}/chat/completions"

        for attempt in range(self._settings.max_retries + 1):
            try:
                response = self._client.post(url, headers=headers, json=payload)
            except (httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
                # A read timeout may happen after the provider accepted a paid generation.
                raise TimeoutError(
                    f"Provider request timed out after {self._settings.timeout_seconds:g} seconds"
                ) from exc
            except httpx.ConnectError as exc:
                if attempt < self._settings.max_retries:
                    self._sleep(self._retry_delay(attempt, None))
                    continue
                raise ProviderError("Could not connect to the configured provider") from exc
            except httpx.RequestError as exc:
                message = "Provider request failed before a response was received"
                raise ProviderError(message) from exc

            if response.status_code in {401, 403}:
                raise AuthenticationError("Provider rejected the configured credentials")

            if response.status_code == 429:
                if attempt < self._settings.max_retries:
                    self._sleep(self._retry_delay(attempt, response))
                    continue
                raise RateLimitError("Provider rate limit remained after retries")

            if 500 <= response.status_code <= 599:
                if attempt < self._settings.max_retries:
                    self._sleep(self._retry_delay(attempt, response))
                    continue
                raise ProviderError(
                    f"Provider returned server error {response.status_code} after retries"
                )

            if response.is_error:
                raise ProviderError(f"Provider returned HTTP {response.status_code}")

            return response

        raise ProviderError("Provider request exhausted its retry policy")

    def _parse(self, response: httpx.Response) -> TextGenerationResult:
        try:
            data = response.json()
            text = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ResponseFormatError("Provider response did not match Chat Completions") from exc

        if not isinstance(text, str) or not text.strip():
            raise ResponseFormatError("Provider returned empty or non-text content")

        return TextGenerationResult(
            text=text.strip(),
            provider="openai_compatible",
            model=self._settings.model,
        )

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
