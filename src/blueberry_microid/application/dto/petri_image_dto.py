from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.petri_image import PetriImage


@dataclass(frozen=True, slots=True)
class RegisterPetriImageRequest:
    """Input for RegisterPetriImageUseCase.

    `content` carries the raw file bytes so the use case can validate and
    store them; `file_size_bytes` is the caller-declared size persisted on
    the record (e.g. computed by an upload handler in a future API layer).
    """

    sample_id: UUID
    file_name: str
    mime_type: str
    file_size_bytes: int
    content: bytes
    captured_at: Optional[datetime] = None
    culture_medium: Optional[str] = None
    incubation_temperature_c: Optional[float] = None
    incubation_time_hours: Optional[float] = None
    seeding_date: Optional[datetime] = None
    observed_colony_color: Optional[str] = None
    observed_colony_shape: Optional[str] = None
    observed_colony_margin: Optional[str] = None
    observed_colony_texture: Optional[str] = None
    notes: Optional[str] = None


@dataclass(frozen=True, slots=True)
class PetriImageDTO:
    """Output representation of a PetriImage, decoupled from the ORM model."""

    id: UUID
    sample_id: UUID
    file_path: str
    file_name: str
    mime_type: str
    file_size_bytes: int
    width: Optional[int]
    height: Optional[int]
    captured_at: Optional[datetime]
    culture_medium: Optional[str]
    incubation_temperature_c: Optional[float]
    incubation_time_hours: Optional[float]
    seeding_date: Optional[datetime]
    observed_colony_color: Optional[str]
    observed_colony_shape: Optional[str]
    observed_colony_margin: Optional[str]
    observed_colony_texture: Optional[str]
    notes: Optional[str]
    created_at: datetime

    @classmethod
    def from_entity(cls, petri_image: PetriImage) -> "PetriImageDTO":
        return cls(
            id=petri_image.id,
            sample_id=petri_image.sample_id,
            file_path=petri_image.file_path,
            file_name=petri_image.file_name,
            mime_type=petri_image.mime_type,
            file_size_bytes=petri_image.file_size_bytes,
            width=petri_image.width,
            height=petri_image.height,
            captured_at=petri_image.captured_at,
            culture_medium=petri_image.culture_medium,
            incubation_temperature_c=petri_image.incubation_temperature_c,
            incubation_time_hours=petri_image.incubation_time_hours,
            seeding_date=petri_image.seeding_date,
            observed_colony_color=petri_image.observed_colony_color,
            observed_colony_shape=petri_image.observed_colony_shape,
            observed_colony_margin=petri_image.observed_colony_margin,
            observed_colony_texture=petri_image.observed_colony_texture,
            notes=petri_image.notes,
            created_at=petri_image.created_at,
        )
