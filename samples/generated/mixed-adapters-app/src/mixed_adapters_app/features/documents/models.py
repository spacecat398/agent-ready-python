"""Provider-independent document contracts."""

from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True, slots=True)
class Document:
    id: str
    source_name: str
    text: str

    @classmethod
    def from_text(cls, source_name: str, text: str) -> "Document":
        source_name = source_name.strip()
        if not source_name:
            raise ValueError("source_name must not be empty")
        if not text.strip():
            raise ValueError("document text must not be empty")
        digest = sha256(f"{source_name}\0{text}".encode()).hexdigest()
        return cls(id=digest, source_name=source_name, text=text)


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    id: str
    document_id: str
    source_name: str
    text: str
    start: int
    end: int

    def __post_init__(self) -> None:
        if not self.text:
            raise ValueError("chunk text must not be empty")
        if self.start < 0 or self.end <= self.start:
            raise ValueError("chunk offsets are invalid")
