"""SQLite Artifact Store implementation."""

import sqlite3
from pathlib import Path
from types import TracebackType
from typing import TypeVar
from uuid import UUID

from pydantic import BaseModel, ValidationError

from agent_ready_python.features.artifacts import (
    Artifact,
    ArtifactNotFoundError,
    ArtifactPersistenceError,
)

PayloadT = TypeVar("PayloadT", bound=BaseModel)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id TEXT PRIMARY KEY,
    artifact_type TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    envelope_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS active_artifacts (
    slot TEXT PRIMARY KEY,
    artifact_id TEXT NOT NULL,
    FOREIGN KEY (artifact_id) REFERENCES artifacts(artifact_id)
);
"""


class SQLiteArtifactStore:
    def __init__(self, database: str | Path = ":memory:") -> None:
        database_value = str(database)
        if database_value != ":memory:":
            parent = Path(database_value).expanduser().resolve().parent
            if not parent.is_dir():
                raise ArtifactPersistenceError(f"Database directory does not exist: {parent}")
        self._connection = sqlite3.connect(database_value)
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.executescript(_SCHEMA)

    def save(self, artifact: Artifact[PayloadT]) -> None:
        serialized = artifact.model_dump_json()
        existing = self._connection.execute(
            "SELECT envelope_json FROM artifacts WHERE artifact_id = ?",
            (str(artifact.id),),
        ).fetchone()
        if existing is not None:
            if existing[0] == serialized:
                return
            raise ArtifactPersistenceError(
                f"Artifact {artifact.id} already exists with different content"
            )

        try:
            with self._connection:
                self._connection.execute(
                    """
                    INSERT INTO artifacts (
                        artifact_id, artifact_type, schema_version, created_at, envelope_json
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(artifact.id),
                        artifact.artifact_type,
                        artifact.schema_version,
                        artifact.created_at.isoformat(),
                        serialized,
                    ),
                )
        except sqlite3.DatabaseError as exc:
            raise ArtifactPersistenceError("Failed to persist artifact") from exc

    def load(
        self,
        artifact_id: UUID,
        payload_type: type[PayloadT],
    ) -> Artifact[PayloadT]:
        row = self._connection.execute(
            "SELECT envelope_json FROM artifacts WHERE artifact_id = ?",
            (str(artifact_id),),
        ).fetchone()
        if row is None:
            raise ArtifactNotFoundError(f"Artifact not found: {artifact_id}")
        try:
            return Artifact[payload_type].model_validate_json(row[0])
        except ValidationError as exc:
            raise ArtifactPersistenceError(
                f"Stored artifact {artifact_id} is incompatible with the requested payload type"
            ) from exc

    def contains(self, artifact_id: UUID) -> bool:
        row = self._connection.execute(
            "SELECT 1 FROM artifacts WHERE artifact_id = ?",
            (str(artifact_id),),
        ).fetchone()
        return row is not None

    def count(self) -> int:
        row = self._connection.execute("SELECT COUNT(*) FROM artifacts").fetchone()
        return int(row[0]) if row is not None else 0

    def activate(self, slot: str, artifact_id: UUID) -> None:
        slot = slot.strip()
        if not slot:
            raise ValueError("activation slot must not be empty")
        if not self.contains(artifact_id):
            raise ArtifactNotFoundError(f"Artifact not found: {artifact_id}")
        try:
            with self._connection:
                self._connection.execute(
                    """
                    INSERT INTO active_artifacts (slot, artifact_id) VALUES (?, ?)
                    ON CONFLICT(slot) DO UPDATE SET artifact_id = excluded.artifact_id
                    """,
                    (slot, str(artifact_id)),
                )
        except sqlite3.DatabaseError as exc:
            raise ArtifactPersistenceError("Failed to activate artifact") from exc

    def active_id(self, slot: str) -> UUID:
        slot = slot.strip()
        if not slot:
            raise ValueError("activation slot must not be empty")
        row = self._connection.execute(
            "SELECT artifact_id FROM active_artifacts WHERE slot = ?",
            (slot,),
        ).fetchone()
        if row is None:
            raise ArtifactNotFoundError(f"No active artifact for slot: {slot}")
        return UUID(row[0])

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "SQLiteArtifactStore":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
