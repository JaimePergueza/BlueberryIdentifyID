from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.image_dataset_audit_status import ImageDatasetAuditStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ImageDatasetAuditRun:
    """Persisted technical audit of the Petri/micro image files referenced by
    a DatasetRelease, ahead of any future training.

    This checks whether image *files* are technically usable (exist, open,
    are not corrupted, have a compatible format/color mode/size) — it never
    opens them as training tensors, never trains a model, and never claims
    microbiological/taxonomic validity. `is_passed` mirrors the meaning of
    `TrainingPreflightRun.is_valid`: true for both PASSED and WARNING (a
    warning does not block future training), false only for FAILED.
    """

    dataset_release_id: UUID
    status: ImageDatasetAuditStatus
    is_passed: bool
    total_items: int
    total_petri_images: int
    total_micro_images: int
    checked_petri_images: int
    checked_micro_images: int
    failed_petri_images: int
    failed_micro_images: int
    warning_count: int
    error_count: int
    summary: dict
    format_distribution: dict
    color_mode_distribution: dict
    dimension_distribution: dict
    file_size_distribution: dict
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_utcnow)
    created_by: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        if self.status == ImageDatasetAuditStatus.FAILED and self.is_passed:
            raise ValueError("failed image dataset audit runs must have is_passed=false")
        if (
            self.status in {ImageDatasetAuditStatus.PASSED, ImageDatasetAuditStatus.WARNING}
            and not self.is_passed
        ):
            raise ValueError("passed/warning image dataset audit runs must have is_passed=true")
