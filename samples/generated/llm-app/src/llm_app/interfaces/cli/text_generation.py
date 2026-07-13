"""CLI commands for the selected text-generation Adapter."""

from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from llm_app.application import AskService
from llm_app.bootstrap import text_generator
from llm_app.features.text_generation import load_text_generation_settings
from llm_app.foundation import AppError
from llm_app.interfaces.cli.common import fail_for_error, resolve_env_file


def register_text_generation_commands(app: typer.Typer) -> None:
    @app.command("llm-check")
    def llm_check(
        env_file: Annotated[Path | None, typer.Option()] = None,
    ) -> None:
        """Validate text-generation configuration without contacting a provider."""

        selected_env = resolve_env_file(env_file)
        try:
            settings = load_text_generation_settings(selected_env)
        except ValidationError as exc:
            fail_for_error(exc)
            return

        typer.echo(f"Provider: {settings.provider}")
        typer.echo(f"Model: {settings.model}")
        typer.echo("API key: not required")

    @app.command()
    def ask(
        prompt: Annotated[str, typer.Argument()],
        env_file: Annotated[Path | None, typer.Option()] = None,
    ) -> None:
        """Generate one non-streaming text response."""

        selected_env = resolve_env_file(env_file)
        try:
            settings = load_text_generation_settings(selected_env)
            with text_generator(settings) as generator:
                result = AskService(generator).ask(prompt)
        except (AppError, ValidationError) as exc:
            fail_for_error(exc)
            return
        except ValueError as exc:
            typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(code=2) from exc

        typer.echo(result.text)
