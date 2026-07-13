"""Settings for the selected offline text-generation Adapter."""

from pathlib import Path
from typing import Any, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class TextGenerationSettings(BaseSettings):
    provider: Literal["fake"] = "fake"
    model: str = "fake"
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
    return TextGenerationSettings(_env_file=env_file, **overrides)
