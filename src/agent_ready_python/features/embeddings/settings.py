"""Settings owned by the optional embeddings feature."""

from pathlib import Path
from typing import Any, Literal

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmbeddingSettings(BaseSettings):
    enabled: bool = False
    provider: Literal["fake", "openai_compatible"] = "fake"
    api_key: SecretStr | None = None
    auth_mode: Literal["bearer", "none"] = "bearer"
    base_url: AnyHttpUrl = "https://api.openai.com/v1"  # type: ignore[assignment]
    model: str = "text-embedding-3-small"
    timeout_seconds: float = Field(default=30.0, gt=0, le=600)
    max_retries: int = Field(default=1, ge=0, le=5)

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
