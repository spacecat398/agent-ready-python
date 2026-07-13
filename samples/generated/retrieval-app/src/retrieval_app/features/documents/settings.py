"""Settings owned by the documents feature."""

from pathlib import Path
from typing import Any

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DocumentSettings(BaseSettings):
    chunk_size: int = Field(default=500, ge=50, le=100_000)
    chunk_overlap: int = Field(default=80, ge=0, le=10_000)
    max_file_bytes: int = Field(default=5_000_000, ge=1, le=100_000_000)

    model_config = SettingsConfigDict(
        env_prefix="AI_DOCUMENTS_",
        env_file=None,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_overlap(self) -> "DocumentSettings":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        return self


def load_document_settings(
    env_file: Path | None = None,
    **overrides: Any,
) -> DocumentSettings:
    return DocumentSettings(_env_file=env_file, **overrides)
