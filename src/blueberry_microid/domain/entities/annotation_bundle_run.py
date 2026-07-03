from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.annotation_bundle_status import AnnotationBundleStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AnnotationBundleRun:
    """A reproducible filesystem bundle plan or completed bundle.

    Stores metadata only: no file contents, image bytes, model artifacts, or
    taxonomy.
    """

    petri_annotation_export_run_id: UUID
    dataset_release_id: UUID
    petri_segmentation_run_id: UUID
    status: AnnotationBundleStatus
    is_completed: bool
    config: dict
    dry_run: bool
    file_count: int
    annotation_count: int
    image_count: int
    label_count: int
    validation_summary: dict
    bundle_manifest: dict
    id: UUID = field(default_factory=uuid4)
    output_dir: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)
    completed_at: Optional[datetime] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None
    error_message: Optional[str] = None

    def __post_init__(self) -> None:
        self.status = AnnotationBundleStatus(self.status)
        if self.status == AnnotationBundleStatus.FAILED and self.is_completed:
            raise ValueError("failed annotation bundle runs cannot be completed")
        if self.status in {AnnotationBundleStatus.COMPLETED, AnnotationBundleStatus.DRY_RUN} and not self.is_completed:
            raise ValueError("completed/dry_run annotation bundle runs must be marked completed")
        if self.status == AnnotationBundleStatus.DRY_RUN and not self.dry_run:
            raise ValueError("dry_run status requires dry_run=true")
