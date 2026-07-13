"""CLI diagnostics contributed by Artifact and Pipeline modules."""

from pathlib import Path
from typing import Annotated

import typer

from agent_ready_python.adapters.sqlite_artifacts import SQLiteArtifactStore
from agent_ready_python.features.artifacts import ArtifactPersistenceError


def register_pipeline_commands(app: typer.Typer) -> None:
    @app.command("pipeline-check")
    def pipeline_check(
        database: Annotated[
            Path | None,
            typer.Option(help="Optional SQLite database path; defaults to in-memory"),
        ] = None,
    ) -> None:
        """Initialize the Artifact Store without running a pipeline."""

        try:
            with SQLiteArtifactStore(database or ":memory:") as store:
                typer.echo("Artifact store: OK")
                typer.echo(f"Stored artifacts: {store.count()}")
                typer.echo("Automatic activation: disabled")
        except ArtifactPersistenceError as exc:
            typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(code=6) from exc
