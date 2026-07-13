"""Pipeline stage and execution models."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel

from agent_ready_python.features.artifacts import Artifact

from .ports import Processor, Validator


@dataclass(frozen=True, slots=True)
class PipelineContext:
    run_id: UUID = field(default_factory=uuid4)
    configuration_version: str | None = None
    metadata: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({})
    )


@dataclass(frozen=True, slots=True)
class PipelineStage[InputT: BaseModel, OutputT: BaseModel]:
    processor: Processor[InputT, OutputT]
    validators: tuple[Validator[OutputT], ...] = ()


@dataclass(frozen=True, slots=True)
class PipelineExecution:
    run_id: UUID
    final_artifact: Artifact[BaseModel]
    produced_artifact_ids: tuple[UUID, ...]
