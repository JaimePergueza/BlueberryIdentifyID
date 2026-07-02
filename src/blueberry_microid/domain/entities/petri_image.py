from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PetriImage:
    """A macro photograph of the Petri dish where microbial growth is observed.

    This is never a photograph of the blueberry fruit itself. It carries the
    file metadata plus the lab-observed growth/culture metadata (medium,
    incubation, and visually observed colony traits) needed for the Petri
    branch of the inference pipeline.
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
    culture_medium: Optional[str] = None
    incubation_temperature_c: Optional[float] = None
    incubation_time_hours: Optional[float] = None
    seeding_date: Optional[datetime] = None
    observed_colony_color: Optional[str] = None
    observed_colony_shape: Optional[str] = None
    observed_colony_margin: Optional[str] = None
    observed_colony_texture: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)
