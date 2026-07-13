"""Pipeline execution errors."""

from artifact_pipeline_app.foundation import AppError


class PipelineCompatibilityError(AppError):
    """A stage cannot consume the current artifact contract."""


class PipelineValidationError(AppError):
    """A stage output failed deterministic validation."""
