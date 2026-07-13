"""Load supported text files without hiding decoding failures."""

from pathlib import Path

from retrieval_app.features.documents import Document
from retrieval_app.foundation import ConfigurationError

_SUPPORTED_SUFFIXES = {".md", ".txt"}


def load_text_document(path: Path, max_file_bytes: int) -> Document:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise ConfigurationError(f"Document does not exist: {resolved}")
    if resolved.suffix.lower() not in _SUPPORTED_SUFFIXES:
        raise ConfigurationError("Only UTF-8 .txt and .md documents are supported")

    size = resolved.stat().st_size
    if size > max_file_bytes:
        raise ConfigurationError(
            f"Document size {size} exceeds configured limit {max_file_bytes}"
        )

    try:
        text = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ConfigurationError(f"Document is not valid UTF-8: {resolved}") from exc

    return Document.from_text(resolved.name, text)
