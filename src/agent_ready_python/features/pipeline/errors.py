"""Pipeline execution errors."""

from agent_ready_python.foundation import AppError


class PipelineCompatibilityError(AppError):
    """A stage cannot consume the current artifact contract."""


class PipelineValidationError(AppError):
    """A stage output failed deterministic validation."""
