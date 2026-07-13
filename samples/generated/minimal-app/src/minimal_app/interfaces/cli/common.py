"""Shared CLI boundary helpers."""

from pathlib import Path

import typer
from pydantic import ValidationError

from minimal_app.foundation import (
    AppError,
    AuthenticationError,
    ConfigurationError,
    RateLimitError,
    TimeoutError,
)


def resolve_env_file(value: Path | None) -> Path | None:
    """Resolve an explicit option or the current project's conventional dotenv path."""

    candidate = value or (Path.cwd() / ".env")
    return candidate.resolve() if candidate.is_file() else None


def fail_for_error(error: AppError | ValidationError) -> None:
    typer.echo(f"Error: {error}", err=True)
    if isinstance(error, (ConfigurationError, ValidationError)):
        raise typer.Exit(code=2)
    if isinstance(error, AuthenticationError):
        raise typer.Exit(code=3)
    if isinstance(error, RateLimitError):
        raise typer.Exit(code=4)
    if isinstance(error, TimeoutError):
        raise typer.Exit(code=5)
    raise typer.Exit(code=6)
