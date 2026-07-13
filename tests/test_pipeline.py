from pathlib import Path

import pytest
from pydantic import BaseModel

from agent_ready_python.adapters.sqlite_artifacts import SQLiteArtifactStore
from agent_ready_python.features.artifacts import (
    Artifact,
    ArtifactProvenance,
    QualityResult,
    ValidationIssue,
)
from agent_ready_python.features.pipeline import (
    PipelineCompatibilityError,
    PipelineRunner,
    PipelineStage,
    PipelineValidationError,
)


class SourcePayload(BaseModel):
    text: str


class CountPayload(BaseModel):
    count: int


class LabelPayload(BaseModel):
    label: str


class SplitWordCounter:
    processor_id = "split-word-counter"
    processor_version = "1.0"
    input_artifact_type = "source.text"
    input_schema_versions = frozenset({"1.0"})
    input_payload_type = SourcePayload
    output_artifact_type = "analysis.word-count"
    output_schema_version = "1.0"
    output_payload_type = CountPayload

    def process(self, payload: SourcePayload, context: object) -> CountPayload:
        return CountPayload(count=len(payload.text.split()))


class CharacterTransitionCounter:
    processor_id = "transition-word-counter"
    processor_version = "1.0"
    input_artifact_type = "source.text"
    input_schema_versions = frozenset({"1.0"})
    input_payload_type = SourcePayload
    output_artifact_type = "analysis.word-count"
    output_schema_version = "1.0"
    output_payload_type = CountPayload

    def process(self, payload: SourcePayload, context: object) -> CountPayload:
        in_word = False
        count = 0
        for character in payload.text:
            if character.isspace():
                in_word = False
            elif not in_word:
                count += 1
                in_word = True
        return CountPayload(count=count)


class CountLabeler:
    processor_id = "count-labeler"
    processor_version = "1.0"
    input_artifact_type = "analysis.word-count"
    input_schema_versions = frozenset({"1.0"})
    input_payload_type = CountPayload
    output_artifact_type = "analysis.label"
    output_schema_version = "1.0"
    output_payload_type = LabelPayload

    def process(self, payload: CountPayload, context: object) -> LabelPayload:
        return LabelPayload(label=f"words:{payload.count}")


class PositiveCountValidator:
    validator_id = "positive-count"
    validator_version = "1.0"

    def validate(self, payload: CountPayload) -> QualityResult:
        if payload.count > 0:
            return QualityResult(
                validator_id=self.validator_id,
                validator_version=self.validator_version,
                passed=True,
            )
        return QualityResult(
            validator_id=self.validator_id,
            validator_version=self.validator_version,
            passed=False,
            issues=(
                ValidationIssue(
                    code="empty-count",
                    message="Word count must be positive",
                    severity="error",
                ),
            ),
        )


def source_artifact(text: str, schema_version: str = "1.0") -> Artifact[SourcePayload]:
    return Artifact[SourcePayload].create(
        artifact_type="source.text",
        schema_version=schema_version,
        provenance=ArtifactProvenance(
            creator_id="test-source",
            creator_version="1.0",
        ),
        payload=SourcePayload(text=text),
    )


def count_stage(processor: object | None = None) -> PipelineStage:
    return PipelineStage(
        processor=processor or SplitWordCounter(),  # type: ignore[arg-type]
        validators=(PositiveCountValidator(),),
    )


def label_stage() -> PipelineStage:
    return PipelineStage(processor=CountLabeler())


def test_pipeline_persists_each_validated_stage() -> None:
    with SQLiteArtifactStore() as store:
        execution = PipelineRunner(store).run(
            source_artifact("one two three"),
            (count_stage(), label_stage()),
        )

        assert store.count() == 3
        assert len(execution.produced_artifact_ids) == 2
        assert execution.final_artifact.payload == LabelPayload(label="words:3")
        assert execution.final_artifact.parent_ids == (
            execution.produced_artifact_ids[0],
        )


def test_failed_validation_does_not_persist_stage_output() -> None:
    initial = source_artifact("   ")
    with SQLiteArtifactStore() as store:
        with pytest.raises(PipelineValidationError, match="empty-count"):
            PipelineRunner(store).run(initial, (count_stage(),))

        assert store.count() == 1
        assert store.contains(initial.id)


def test_failed_replacement_does_not_change_active_artifact() -> None:
    active = source_artifact("existing")
    replacement = source_artifact("   ")
    with SQLiteArtifactStore() as store:
        store.save(active)
        store.activate("current", active.id)

        with pytest.raises(PipelineValidationError):
            PipelineRunner(store).run(replacement, (count_stage(),))

        assert store.active_id("current") == active.id


def test_pipeline_resumes_from_persisted_intermediate_artifact(tmp_path: Path) -> None:
    database = tmp_path / "pipeline.db"
    with SQLiteArtifactStore(database) as store:
        first_execution = PipelineRunner(store).run(
            source_artifact("one two"),
            (count_stage(),),
        )
        intermediate_id = first_execution.final_artifact.id

    with SQLiteArtifactStore(database) as reopened:
        resumed = PipelineRunner(reopened).resume(
            intermediate_id,
            CountPayload,
            (label_stage(),),
        )

        assert reopened.count() == 3
        assert resumed.final_artifact.payload == LabelPayload(label="words:2")


@pytest.mark.parametrize("processor", [SplitWordCounter(), CharacterTransitionCounter()])
def test_processor_implementations_are_replaceable(processor: object) -> None:
    with SQLiteArtifactStore() as store:
        execution = PipelineRunner(store).run(
            source_artifact("one two three"),
            (count_stage(processor), label_stage()),
        )

    assert execution.final_artifact.payload == LabelPayload(label="words:3")


def test_pipeline_rejects_unknown_input_schema_before_processing() -> None:
    with SQLiteArtifactStore() as store:
        with pytest.raises(PipelineCompatibilityError, match="does not support schema"):
            PipelineRunner(store).run(
                source_artifact("text", schema_version="2.0"),
                (count_stage(),),
            )

        assert store.count() == 1
