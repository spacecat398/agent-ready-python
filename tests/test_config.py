from pathlib import Path

import pytest
from pydantic import ValidationError

from agent_ready_python.features.documents import DocumentSettings
from agent_ready_python.features.embeddings import load_embedding_settings
from agent_ready_python.features.text_generation import load_text_generation_settings
from agent_ready_python.foundation import load_core_settings


def test_core_settings_defaults() -> None:
    settings = load_core_settings()

    assert settings.app_name == "agent-ready-python"
    assert settings.log_level == "INFO"


def test_explicit_env_file_is_loaded(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("AI_LOG_LEVEL=debug\nAI_LLM_PROVIDER=fake\n", encoding="utf-8")

    assert load_core_settings(env_file).log_level == "DEBUG"
    assert load_text_generation_settings(env_file).provider == "fake"


def test_invalid_retry_count_fails_early() -> None:
    with pytest.raises(ValidationError):
        load_text_generation_settings(max_retries=99)


def test_local_provider_can_disable_authentication() -> None:
    settings = load_text_generation_settings(
        provider="openai_compatible",
        auth_mode="none",
        base_url="http://127.0.0.1:8000/v1",
    )

    assert settings.api_key is None
    assert settings.auth_mode == "none"


def test_remote_embeddings_are_disabled_by_default() -> None:
    settings = load_embedding_settings(api_key="host-key")

    assert settings.enabled is False


def test_document_overlap_validation() -> None:
    with pytest.raises(ValidationError):
        DocumentSettings(chunk_size=100, chunk_overlap=100)
