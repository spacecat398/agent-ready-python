"""CLI commands for documents and local retrieval."""

from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from mixed_adapters_app.adapters.filesystem import load_text_document
from mixed_adapters_app.bootstrap import document_retriever
from mixed_adapters_app.features.documents import TextChunker, load_document_settings
from mixed_adapters_app.features.embeddings import load_embedding_settings
from mixed_adapters_app.features.retrieval import RetrievalService
from mixed_adapters_app.foundation import AppError
from mixed_adapters_app.interfaces.cli.common import fail_for_error, resolve_env_file


def register_retrieval_commands(app: typer.Typer) -> None:
    @app.command("retrieval-check")
    def retrieval_check(
        env_file: Annotated[Path | None, typer.Option()] = None,
    ) -> None:
        """Validate retrieval configuration without using a provider."""

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
        document: Annotated[Path, typer.Argument()],
        query: Annotated[str, typer.Argument()],
        top_k: Annotated[int, typer.Option(min=1, max=20)] = 3,
        env_file: Annotated[Path | None, typer.Option()] = None,
    ) -> None:
        """Search one text document locally by default."""

        selected_env = resolve_env_file(env_file)
        try:
            document_settings = load_document_settings(selected_env)
            embedding_settings = load_embedding_settings(selected_env)
            loaded = load_text_document(
                document, document_settings.max_file_bytes
            )
            chunks = TextChunker(document_settings).split(loaded)
            with document_retriever(chunks, embedding_settings) as retriever:
                matches = RetrievalService(retriever).search(query, top_k)
        except (AppError, ValidationError) as exc:
            fail_for_error(exc)
            return

        if not matches:
            typer.echo("No matching chunks")
            return
        for match in matches:
            typer.echo(
                f"[{match.score:.3f}] {match.chunk.source_name}:"
                f"{match.chunk.start}-{match.chunk.end}"
            )
            typer.echo(match.chunk.text)
