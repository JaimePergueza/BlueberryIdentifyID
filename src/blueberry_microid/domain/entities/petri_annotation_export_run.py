from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.petri_annotation_export_format import PetriAnnotationExportFormat
from blueberry_microid.domain.enums.petri_annotation_export_status import PetriAnnotationExportStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PetriAnnotationExportRun:
    """One persisted supervised annotation export for reviewed Petri regions.

    It stores metadata and JSON payloads only. It never stores image bytes,
    masks, taxonomy, training state, or model artifacts.
    """

    dataset_release_id: UUID
    petri_segmentation_run_id: UUID
    export_format: PetriAnnotationExportFormat
    status: PetriAnnotationExportStatus
    is_completed: bool
    config: dict
    exported_annotation_count: int
    skipped_review_count: int
    image_count: int
    category_count: int
    output_manifest: dict
    summary: dict
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_utcnow)
    completed_at: Optional[datetime] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None
    error_message: Optional[str] = None

    def __post_init__(self) -> None:
        self.export_format = PetriAnnotationExportFormat(self.export_format)
        self.status = PetriAnnotationExportStatus(self.status)
        if self.status == PetriAnnotationExportStatus.FAILED and self.is_completed:
            raise ValueError("failed annotation export runs cannot be completed")
        if self.status in {
            PetriAnnotationExportStatus.COMPLETED,
            PetriAnnotationExportStatus.PARTIAL,
        } and not self.is_completed:
            raise ValueError("completed or partial annotation export runs must be marked completed")
