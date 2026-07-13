"""Artifact-specific persistence errors."""

from artifact_pipeline_app.foundation import AppError


class ArtifactPersistenceError(AppError):
    """An artifact could not be persisted without violating append-only rules."""


class ArtifactNotFoundError(AppError):
    """A requested artifact or active artifact reference does not exist."""
