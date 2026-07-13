"""Settings owned by the optional text-generation feature."""

from pathlib import Path
from typing import Any, Literal

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class TextGenerationSettings(BaseSettings):
    provider: Literal["fake", "openai_compatible"] = "fake"
    api_key: SecretStr | None = None
    auth_mode: Literal["bearer", "none"] = "bearer"
    base_url: AnyHttpUrl = "https://api.openai.com/v1"  # type: ignore[assignment]
    model: str = "gpt-4o-mini"
    timeout_seconds: float = Field(default=60.0, gt=0, le=600)
    max_retries: int = Field(default=2, ge=0, le=5)
    fake_response: str = "Fake provider response"

    model_config = SettingsConfigDict(
        env_prefix="AI_LLM_",
        env_file=None,
        extra="ignore",
    )

    @field_validator("model", "fake_response")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value


def load_text_generation_settings(
    env_file: Path | None = None,
    **overrides: Any,
) -> TextGenerationSettings:
    """Load feature settings from environment and an explicitly selected dotenv file."""

    return TextGenerationSettings(_env_file=env_file, **overrides)
