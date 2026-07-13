"""Processor and Validator contracts."""

from typing import Protocol, TypeVar

from pydantic import BaseModel

from artifact_pipeline_app.features.artifacts import QualityResult

InputT = TypeVar("InputT", bound=BaseModel, contravariant=True)
OutputT = TypeVar("OutputT", bound=BaseModel, covariant=True)
ValidatedT = TypeVar("ValidatedT", bound=BaseModel, contravariant=True)


class Processor(Protocol[InputT, OutputT]):
    processor_id: str
    processor_version: str
    input_artifact_type: str
    input_schema_versions: frozenset[str]
    input_payload_type: type[InputT]
    output_artifact_type: str
    output_schema_version: str
    output_payload_type: type[OutputT]

    def process(self, payload: InputT, context: object) -> OutputT: ...


class Validator(Protocol[ValidatedT]):
    validator_id: str
    validator_version: str

    def validate(self, payload: ValidatedT) -> QualityResult: ...
