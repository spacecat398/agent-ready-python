"""CLI commands contributed by the optional text-generation feature."""

from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from agent_ready_python.application import AskService
from agent_ready_python.bootstrap import text_generator
from agent_ready_python.features.text_generation import load_text_generation_settings
from agent_ready_python.foundation import AppError
from agent_ready_python.interfaces.cli.common import fail_for_error, resolve_env_file


def register_text_generation_commands(app: typer.Typer) -> None:
    @app.command("llm-check")
    def llm_check(
        env_file: Annotated[
            Path | None,
            typer.Option(help="Optional dotenv file to load"),
        ] = None,
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
        typer.echo(f"Base URL: {settings.base_url}")
        if settings.provider == "fake" or settings.auth_mode == "none":
            typer.echo("API key: not required")
        else:
            typer.echo(f"API key: {'configured' if settings.api_key else 'missing'}")

    @app.command()
    def ask(
        prompt: Annotated[str, typer.Argument(help="Prompt to send to the configured provider")],
        env_file: Annotated[
            Path | None,
            typer.Option(help="Optional dotenv file to load"),
        ] = None,
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
