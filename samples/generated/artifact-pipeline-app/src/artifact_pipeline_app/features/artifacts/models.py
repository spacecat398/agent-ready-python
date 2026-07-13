"""Immutable, typed and versioned artifact envelope."""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ValidationIssue(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    severity: Literal["error", "warning"]


class QualityResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    validator_id: str = Field(min_length=1)
    validator_version: str = Field(pattern=r"^\d+\.\d+$")
    passed: bool
    issues: tuple[ValidationIssue, ...] = ()

    @model_validator(mode="after")
    def validate_result(self) -> "QualityResult":
        has_error = any(issue.severity == "error" for issue in self.issues)
        if self.passed == has_error:
            raise ValueError("passed must be false exactly when error issues are present")
        return self


class ArtifactProvenance(BaseModel):
    model_config = ConfigDict(frozen=True)

    creator_id: str = Field(min_length=1)
    creator_version: str = Field(pattern=r"^\d+\.\d+$")
    configuration_version: str | None = None


class Artifact[PayloadT: BaseModel](BaseModel):
    """An append-only envelope around one validated typed payload."""

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    artifact_type: str = Field(pattern=r"^[a-z][a-z0-9_.-]*$")
    schema_version: str = Field(pattern=r"^\d+\.\d+$")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    provenance: ArtifactProvenance
    parent_ids: tuple[UUID, ...] = ()
    quality: tuple[QualityResult, ...] = ()
    payload: PayloadT

    @model_validator(mode="after")
    def validate_identity_and_time(self) -> "Artifact[PayloadT]":
        if len(self.parent_ids) != len(set(self.parent_ids)):
            raise ValueError("parent artifact IDs must be unique")
        if self.id in self.parent_ids:
            raise ValueError("an artifact cannot be its own parent")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must include timezone information")
        if any(not result.passed for result in self.quality):
            raise ValueError("persisted artifacts may contain only passed quality results")
        return self

    @classmethod
    def create(
        cls,
        *,
        artifact_type: str,
        schema_version: str,
        provenance: ArtifactProvenance,
        payload: PayloadT,
        parent_ids: tuple[UUID, ...] = (),
        quality: tuple[QualityResult, ...] = (),
    ) -> "Artifact[PayloadT]":
        return cls(
            artifact_type=artifact_type,
            schema_version=schema_version,
            provenance=provenance,
            parent_ids=parent_ids,
            quality=quality,
            payload=payload,
        )
