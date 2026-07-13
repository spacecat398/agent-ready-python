from pathlib import Path

import pytest
from pydantic import ValidationError

from agent_ready_python.adapters.filesystem import load_text_document
from agent_ready_python.features.documents import (
    Document,
    DocumentSettings,
    TextChunker,
)
from agent_ready_python.foundation import ConfigurationError


def test_chunking_is_deterministic_and_overlapping() -> None:
    document = Document.from_text("notes.txt", "a" * 80)
    settings = DocumentSettings(chunk_size=60, chunk_overlap=20)

    first = TextChunker(settings).split(document)
    second = TextChunker(settings).split(document)

    assert [len(chunk.text) for chunk in first] == [60, 40]
    assert first == second
    assert first[0].start == 0
    assert first[1].start == 40


def test_overlap_must_be_smaller_than_chunk_size() -> None:
    with pytest.raises(ValidationError):
        DocumentSettings(chunk_size=50, chunk_overlap=50)


def test_filesystem_adapter_loads_utf8_text(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("模块化检索", encoding="utf-8")

    document = load_text_document(path, max_file_bytes=100)

    assert document.source_name == "notes.txt"
    assert document.text == "模块化检索"


def test_document_preserves_source_whitespace_for_stable_offsets() -> None:
    document = Document.from_text("notes.txt", "  content\n")

    assert document.text == "  content\n"


def test_filesystem_adapter_rejects_invalid_utf8(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_bytes(b"\xff\xfe")

    with pytest.raises(ConfigurationError, match="valid UTF-8"):
        load_text_document(path, max_file_bytes=100)


def test_filesystem_adapter_enforces_size_limit(tmp_path: Path) -> None:
    path = tmp_path / "notes.md"
    path.write_text("too large", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="exceeds configured limit"):
        load_text_document(path, max_file_bytes=2)
