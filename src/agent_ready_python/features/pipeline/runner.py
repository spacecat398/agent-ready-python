"""Sequential pipeline runner with validation gates and stage persistence."""

from typing import Any, TypeVar, cast
from uuid import UUID

from pydantic import BaseModel

from agent_ready_python.features.artifacts import (
    Artifact,
    ArtifactProvenance,
    ArtifactStore,
)

from .errors import PipelineCompatibilityError, PipelineValidationError
from .models import PipelineContext, PipelineExecution, PipelineStage

PayloadT = TypeVar("PayloadT", bound=BaseModel)


class PipelineRunner:
    def __init__(self, store: ArtifactStore) -> None:
        self._store = store

    def run(
        self,
        initial: Artifact[PayloadT],
        stages: tuple[PipelineStage[Any, Any], ...],
        context: PipelineContext | None = None,
    ) -> PipelineExecution:
        execution_context = context or PipelineContext()
        self._store.save(initial)
        current = cast(Artifact[BaseModel], initial)
        produced_ids: list[UUID] = []

        for stage in stages:
            processor = stage.processor
            self._check_compatibility(current, stage)
            output = processor.process(current.payload, execution_context)
            if not isinstance(output, processor.output_payload_type):
                raise PipelineCompatibilityError(
                    f"Processor {processor.processor_id} returned "
                    f"{type(output).__name__}, expected {processor.output_payload_type.__name__}"
                )

            quality = tuple(validator.validate(output) for validator in stage.validators)
            failures = [result for result in quality if not result.passed]
            if failures:
                issue_codes = [
                    issue.code for result in failures for issue in result.issues
                ]
                raise PipelineValidationError(
                    f"Stage {processor.processor_id} failed validation: {issue_codes}"
                )

            next_artifact = Artifact[processor.output_payload_type].create(
                artifact_type=processor.output_artifact_type,
                schema_version=processor.output_schema_version,
                provenance=ArtifactProvenance(
                    creator_id=processor.processor_id,
                    creator_version=processor.processor_version,
                    configuration_version=execution_context.configuration_version,
                ),
                parent_ids=(current.id,),
                quality=quality,
                payload=output,
            )
            self._store.save(next_artifact)
            produced_ids.append(next_artifact.id)
            current = cast(Artifact[BaseModel], next_artifact)

        return PipelineExecution(
            run_id=execution_context.run_id,
            final_artifact=current,
            produced_artifact_ids=tuple(produced_ids),
        )

    def resume(
        self,
        artifact_id: UUID,
        payload_type: type[PayloadT],
        stages: tuple[PipelineStage[Any, Any], ...],
        context: PipelineContext | None = None,
    ) -> PipelineExecution:
        initial = self._store.load(artifact_id, payload_type)
        return self.run(initial, stages, context)

    @staticmethod
    def _check_compatibility(
        artifact: Artifact[BaseModel],
        stage: PipelineStage[Any, Any],
    ) -> None:
        processor = stage.processor
        if artifact.artifact_type != processor.input_artifact_type:
            raise PipelineCompatibilityError(
                f"Processor {processor.processor_id} expects artifact type "
                f"{processor.input_artifact_type}, got {artifact.artifact_type}"
            )
        if artifact.schema_version not in processor.input_schema_versions:
            raise PipelineCompatibilityError(
                f"Processor {processor.processor_id} does not support schema "
                f"{artifact.schema_version}"
            )
        if not isinstance(artifact.payload, processor.input_payload_type):
            raise PipelineCompatibilityError(
                f"Processor {processor.processor_id} expects payload "
                f"{processor.input_payload_type.__name__}, got "
                f"{type(artifact.payload).__name__}"
            )
