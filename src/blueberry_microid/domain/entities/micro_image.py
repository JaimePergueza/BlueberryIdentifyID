from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class MicroImage:
    """A microscopy photograph taken from the sample plated on a PetriImage.

    Carries file metadata plus microscopy-specific metadata (magnification,
    microscope type, staining/preparation). `observed_structures` is free-text
    morphological notes (hyphae, spores, conidia, etc.) and must never encode
    a taxonomic identification.
    """

    sample_id: UUID
    file_path: str
    file_name: str
    mime_type: str
    file_size_bytes: int
    id: UUID = field(default_factory=uuid4)
    width: Optional[int] = None
    height: Optional[int] = None
    captured_at: Optional[datetime] = None
    magnification: Optional[str] = None
    microscope_type: Optional[str] = None
    staining_method: Optional[str] = None
    preparation_method: Optional[str] = None
    observed_structures: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)
