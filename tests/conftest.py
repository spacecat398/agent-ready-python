"""Global test safety fixtures."""

import socket

import pytest

_AI_ENV_VARS = (
    "AI_APP_NAME",
    "AI_LOG_LEVEL",
    "AI_LLM_PROVIDER",
    "AI_LLM_API_KEY",
    "AI_LLM_AUTH_MODE",
    "AI_LLM_BASE_URL",
    "AI_LLM_MODEL",
    "AI_LLM_TIMEOUT_SECONDS",
    "AI_LLM_MAX_RETRIES",
    "AI_LLM_FAKE_RESPONSE",
    "AI_DOCUMENTS_CHUNK_SIZE",
    "AI_DOCUMENTS_CHUNK_OVERLAP",
    "AI_DOCUMENTS_MAX_FILE_BYTES",
    "AI_EMBEDDING_ENABLED",
    "AI_EMBEDDING_PROVIDER",
    "AI_EMBEDDING_API_KEY",
    "AI_EMBEDDING_AUTH_MODE",
    "AI_EMBEDDING_BASE_URL",
    "AI_EMBEDDING_MODEL",
    "AI_EMBEDDING_TIMEOUT_SECONDS",
    "AI_EMBEDDING_MAX_RETRIES",
)


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _AI_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked_connect(*_: object, **__: object) -> None:
        raise RuntimeError("Network access is blocked during tests")

    monkeypatch.setattr(socket.socket, "connect", blocked_connect)
