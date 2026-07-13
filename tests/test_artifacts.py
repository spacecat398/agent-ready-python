from pathlib import Path
from uuid import UUID

import pytest
from pydantic import BaseModel, ValidationError

from agent_ready_python.adapters.sqlite_artifacts import SQLiteArtifactStore
from agent_ready_python.features.artifacts import (
    Artifact,
    ArtifactPersistenceError,
    ArtifactProvenance,
    QualityResult,
    ValidationIssue,
)


class TextPayload(BaseModel):
    text: str


def make_artifact(text: str = "hello") -> Artifact[TextPayload]:
    return Artifact[TextPayload].create(
        artifact_type="source.text",
        schema_version="1.0",
        provenance=ArtifactProvenance(
            creator_id="test",
            creator_version="1.0",
        ),
        payload=TextPayload(text=text),
    )


def test_artifact_is_frozen_and_timezone_aware() -> None:
    artifact = make_artifact()

    assert artifact.created_at.utcoffset() is not None
    with pytest.raises(ValidationError):
        artifact.artifact_type = "changed"  # type: ignore[misc]


def test_artifact_rejects_duplicate_parents() -> None:
    parent = make_artifact()

    with pytest.raises(ValidationError, match="unique"):
        Artifact[TextPayload].create(
            artifact_type="derived.text",
            schema_version="1.0",
            provenance=ArtifactProvenance(
                creator_id="test",
                creator_version="1.0",
            ),
            parent_ids=(parent.id, parent.id),
            payload=TextPayload(text="derived"),
        )


def test_failed_quality_result_requires_error_issue() -> None:
    result = QualityResult(
        validator_id="non-empty",
        validator_version="1.0",
        passed=False,
        issues=(
            ValidationIssue(code="empty", message="Text is empty", severity="error"),
        ),
    )

    assert result.passed is False


def test_sqlite_store_round_trips_typed_artifact(tmp_path: Path) -> None:
    database = tmp_path / "artifacts.db"
    artifact = make_artifact()

    with SQLiteArtifactStore(database) as store:
        store.save(artifact)
        loaded = store.load(artifact.id, TextPayload)

    assert loaded == artifact
    assert isinstance(loaded.id, UUID)
    assert isinstance(loaded.payload, TextPayload)


def test_sqlite_store_is_idempotent_but_append_only() -> None:
    artifact = make_artifact()
    changed = artifact.model_copy(update={"payload": TextPayload(text="changed")})

    with SQLiteArtifactStore() as store:
        store.save(artifact)
        store.save(artifact)
        with pytest.raises(ArtifactPersistenceError, match="different content"):
            store.save(changed)

        assert store.count() == 1


def test_activation_is_explicit_and_replaceable() -> None:
    first = make_artifact("first")
    second = make_artifact("second")

    with SQLiteArtifactStore() as store:
        store.save(first)
        store.save(second)
        store.activate("current-route", first.id)
        assert store.active_id(" current-route ") == first.id

        store.activate("current-route", second.id)
        assert store.active_id("current-route") == second.id
