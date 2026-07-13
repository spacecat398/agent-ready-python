"""Provider-independent application settings."""

from pathlib import Path
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}


class CoreSettings(BaseSettings):
    """Settings required even when every optional AI feature is removed."""

    app_name: str = "agent-ready-python"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_prefix="AI_",
        env_file=None,
        extra="ignore",
    )

    @field_validator("app_name")
    @classmethod
    def validate_app_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("app_name must not be empty")
        return value

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        value = value.upper().strip()
        if value not in _LOG_LEVELS:
            raise ValueError(f"log_level must be one of {sorted(_LOG_LEVELS)}")
        return value


def load_core_settings(env_file: Path | None = None, **overrides: Any) -> CoreSettings:
    """Load settings, reading a dotenv file only when its path is explicit."""

    return CoreSettings(_env_file=env_file, **overrides)
