"""SQLite persistence for immutable artifacts and mutable active references."""

from .store import SQLiteArtifactStore

__all__ = ["SQLiteArtifactStore"]
