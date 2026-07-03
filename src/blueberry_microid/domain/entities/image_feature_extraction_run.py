from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.image_feature_extraction_status import ImageFeatureExtractionStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ImageFeatureExtractionRun:
    """Persisted result of extracting simple, non-deep, reproducible
    features from the Petri/micro images referenced by a DatasetRelease
    whose ImageDatasetAuditRun was not failed.

    This never stores image bytes, tensors, trained model artifacts, or
    classification metrics — only small technical feature scalars
    (see ImageFeatureVector) plus run-level bookkeeping.
    """

    dataset_release_id: UUID
    image_audit_run_id: UUID
    status: ImageFeatureExtractionStatus
    is_completed: bool
    config: dict
    total_items: int
    processed_items: int
    failed_items: int
    total_feature_vectors: int
    petri_feature_count: int
    micro_feature_count: int
    summary: dict
    started_at: datetime
    id: UUID = field(default_factory=uuid4)
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=_utcnow)
    created_by: Optional[str] = None
    notes: Optional[str] = None
    error_message: Optional[str] = None

    def __post_init__(self) -> None:
        # `is_completed` tracks whether the run finished running at all (as
        # opposed to aborting before extraction started, e.g. an invalid
        # audit) — not whether every item succeeded. COMPLETED and PARTIAL
        # both represent a run that ran to completion; only FAILED means it
        # did not.
        if self.status == ImageFeatureExtractionStatus.FAILED and self.is_completed:
            raise ValueError("failed image feature extraction runs must have is_completed=false")
        if (
            self.status in {ImageFeatureExtractionStatus.COMPLETED, ImageFeatureExtractionStatus.PARTIAL}
            and not self.is_completed
        ):
            raise ValueError("completed/partial image feature extraction runs must have is_completed=true")
