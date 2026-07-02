from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.micro_image import MicroImage


@dataclass(frozen=True, slots=True)
class RegisterMicroImageRequest:
    """Input for RegisterMicroImageUseCase. See RegisterPetriImageRequest for
    the rationale behind carrying both `content` and `file_size_bytes`.
    """

    sample_id: UUID
    file_name: str
    mime_type: str
    file_size_bytes: int
    content: bytes
    captured_at: Optional[datetime] = None
    magnification: Optional[str] = None
    microscope_type: Optional[str] = None
    staining_method: Optional[str] = None
    preparation_method: Optional[str] = None
    observed_structures: Optional[str] = None
    notes: Optional[str] = None


@dataclass(frozen=True, slots=True)
class MicroImageDTO:
    """Output representation of a MicroImage, decoupled from the ORM model."""

    id: UUID
    sample_id: UUID
    file_path: str
    file_name: str
    mime_type: str
    file_size_bytes: int
    width: Optional[int]
    height: Optional[int]
    captured_at: Optional[datetime]
    magnification: Optional[str]
    microscope_type: Optional[str]
    staining_method: Optional[str]
    preparation_method: Optional[str]
    observed_structures: Optional[str]
    notes: Optional[str]
    created_at: datetime

    @classmethod
    def from_entity(cls, micro_image: MicroImage) -> "MicroImageDTO":
        return cls(
            id=micro_image.id,
            sample_id=micro_image.sample_id,
            file_path=micro_image.file_path,
            file_name=micro_image.file_name,
            mime_type=micro_image.mime_type,
            file_size_bytes=micro_image.file_size_bytes,
            width=micro_image.width,
            height=micro_image.height,
            captured_at=micro_image.captured_at,
            magnification=micro_image.magnification,
            microscope_type=micro_image.microscope_type,
            staining_method=micro_image.staining_method,
            preparation_method=micro_image.preparation_method,
            observed_structures=micro_image.observed_structures,
            notes=micro_image.notes,
            created_at=micro_image.created_at,
        )
