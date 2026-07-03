from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.petri_segmentation_status import PetriSegmentationStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class PetriSegmentationRun:
    """Persisted classical segmentation pass over Petri images only.

    It stores run bookkeeping and a technical summary, never image bytes,
    masks, model artifacts, taxonomy, or microbiological diagnosis.
    """

    dataset_release_id: UUID
    status: PetriSegmentationStatus
    is_completed: bool
    config: dict
    total_items: int
    processed_petri_images: int
    failed_petri_images: int
    total_regions_detected: int
    summary: dict
    started_at: datetime
    id: UUID = field(default_factory=uuid4)
    image_audit_run_id: Optional[UUID] = None
    mean_regions_per_image: Optional[float] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=_utcnow)
    created_by: Optional[str] = None
    notes: Optional[str] = None
    error_message: Optional[str] = None

    def __post_init__(self) -> None:
        if self.status == PetriSegmentationStatus.FAILED and self.is_completed:
            raise ValueError("failed Petri segmentation runs must have is_completed=false")
        if self.status in {PetriSegmentationStatus.COMPLETED, PetriSegmentationStatus.PARTIAL} and not self.is_completed:
            raise ValueError("completed/partial Petri segmentation runs must have is_completed=true")
