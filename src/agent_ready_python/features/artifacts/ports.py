"""Persistence ports owned by the artifact feature."""

from typing import Protocol, TypeVar
from uuid import UUID

from pydantic import BaseModel

from .models import Artifact

PayloadT = TypeVar("PayloadT", bound=BaseModel)


class ArtifactStore(Protocol):
    def save(self, artifact: Artifact[PayloadT]) -> None: ...

    def load(
        self,
        artifact_id: UUID,
        payload_type: type[PayloadT],
    ) -> Artifact[PayloadT]: ...

    def contains(self, artifact_id: UUID) -> bool: ...

    def count(self) -> int: ...


class ArtifactActivationStore(Protocol):
    def activate(self, slot: str, artifact_id: UUID) -> None: ...

    def active_id(self, slot: str) -> UUID: ...
