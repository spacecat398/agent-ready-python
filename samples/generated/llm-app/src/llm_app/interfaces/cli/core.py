"""Core CLI commands that survive removal of every optional AI feature."""

from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from llm_app import __version__
from llm_app.foundation import load_core_settings
from llm_app.foundation.logging import configure_logging
from llm_app.interfaces.cli.common import fail_for_error, resolve_env_file


def create_core_cli() -> typer.Typer:
    app = typer.Typer(no_args_is_help=True, help="Modular Python AI application starter")

    @app.command()
    def version() -> None:
        """Print the application version."""

        typer.echo(__version__)

    @app.command()
    def check(
        env_file: Annotated[
            Path | None,
            typer.Option(help="Optional dotenv file to load"),
        ] = None,
    ) -> None:
        """Validate provider-independent application configuration."""

        selected_env = resolve_env_file(env_file)
        try:
            settings = load_core_settings(selected_env)
        except ValidationError as exc:
            fail_for_error(exc)
            return

        configure_logging(settings.log_level)
        typer.echo("Python: OK")
        typer.echo(f"Application: {settings.app_name}")
        typer.echo(f"Log level: {settings.log_level}")
        typer.echo(f"Environment file: {selected_env if selected_env else 'not loaded'}")

    return app
