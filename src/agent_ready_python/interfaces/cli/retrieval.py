"""CLI commands contributed by documents, retrieval, and optional embeddings."""

from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from agent_ready_python.adapters.filesystem import load_text_document
from agent_ready_python.bootstrap import document_retriever
from agent_ready_python.features.documents import TextChunker, load_document_settings
from agent_ready_python.features.embeddings import load_embedding_settings
from agent_ready_python.features.retrieval import RetrievalService
from agent_ready_python.foundation import AppError
from agent_ready_python.interfaces.cli.common import fail_for_error, resolve_env_file


def register_retrieval_commands(app: typer.Typer) -> None:
    @app.command("retrieval-check")
    def retrieval_check(
        env_file: Annotated[
            Path | None,
            typer.Option(help="Optional dotenv file to load"),
        ] = None,
    ) -> None:
        """Validate retrieval configuration without loading documents or using a provider."""

        selected_env = resolve_env_file(env_file)
        try:
            document_settings = load_document_settings(selected_env)
            embedding_settings = load_embedding_settings(selected_env)
        except ValidationError as exc:
            fail_for_error(exc)
            return

        typer.echo(f"Chunk size: {document_settings.chunk_size}")
        typer.echo(f"Chunk overlap: {document_settings.chunk_overlap}")
        typer.echo(
            f"Retrieval mode: {'semantic' if embedding_settings.enabled else 'keyword'}"
        )
        if embedding_settings.enabled:
            typer.echo(f"Embedding provider: {embedding_settings.provider}")
            typer.echo(f"Embedding model: {embedding_settings.model}")

    @app.command()
    def search(
        document: Annotated[Path, typer.Argument(help="UTF-8 .txt or .md document")],
        query: Annotated[str, typer.Argument(help="Question or search query")],
        top_k: Annotated[int, typer.Option(min=1, max=20)] = 3,
        env_file: Annotated[
            Path | None,
            typer.Option(help="Optional dotenv file to load"),
        ] = None,
    ) -> None:
        """Search one text document with local keyword retrieval by default."""

        selected_env = resolve_env_file(env_file)
        try:
            document_settings = load_document_settings(selected_env)
            embedding_settings = load_embedding_settings(selected_env)
            loaded = load_text_document(document, document_settings.max_file_bytes)
            chunks = TextChunker(document_settings).split(loaded)
            with document_retriever(chunks, embedding_settings) as retriever:
                matches = RetrievalService(retriever).search(query, top_k)
        except (AppError, ValidationError) as exc:
            fail_for_error(exc)
            return
        except ValueError as exc:
            typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(code=2) from exc

        if not matches:
            typer.echo("No matching chunks")
            return

        for match in matches:
            typer.echo(
                f"[{match.score:.3f}] {match.chunk.source_name}:"
                f"{match.chunk.start}-{match.chunk.end}"
            )
            typer.echo(match.chunk.text)
