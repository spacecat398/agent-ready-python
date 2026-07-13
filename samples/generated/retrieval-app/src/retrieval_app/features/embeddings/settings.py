"""Settings for the selected offline embedding Adapter."""

from pathlib import Path
from typing import Any, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmbeddingSettings(BaseSettings):
    enabled: bool = False
    provider: Literal["fake"] = "fake"
    model: str = "sha256-8"

    model_config = SettingsConfigDict(
        env_prefix="AI_EMBEDDING_",
        env_file=None,
        extra="ignore",
    )

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("embedding model must not be empty")
        return value


def load_embedding_settings(
    env_file: Path | None = None,
    **overrides: Any,
) -> EmbeddingSettings:
    return EmbeddingSettings(_env_file=env_file, **overrides)
