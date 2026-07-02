from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.model_version import ModelVersion


@dataclass(frozen=True, slots=True)
class CreateModelVersionRequest:
    """Input for CreateModelVersionUseCase.

    `model_type` is accepted as a raw string (not the ModelType enum)
    because, until the API layer exists, callers may not have imported the
    domain enum; the use case validates and converts it.
    """

    name: str
    version: str
    model_type: str
    description: Optional[str] = None
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class ModelVersionDTO:
    """Output representation of a ModelVersion, decoupled from the ORM model."""

    id: UUID
    name: str
    version: str
    model_type: str
    description: Optional[str]
    is_active: bool
    created_at: datetime

    @classmethod
    def from_entity(cls, model_version: ModelVersion) -> "ModelVersionDTO":
        return cls(
            id=model_version.id,
            name=model_version.name,
            version=model_version.version,
            model_type=model_version.model_type.value,
            description=model_version.description,
            is_active=model_version.is_active,
            created_at=model_version.created_at,
        )
