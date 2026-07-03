from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.annotation_quality_gate_status import AnnotationQualityGateStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AnnotationQualityGateRun:
    """Persisted technical readiness report for one annotation bundle."""

    annotation_bundle_run_id: UUID
    dataset_release_id: UUID
    petri_annotation_export_run_id: UUID
    status: AnnotationQualityGateStatus
    is_passed: bool
    config: dict
    total_images: int
    total_annotations: int
    train_image_count: int
    validation_image_count: int
    test_image_count: int
    train_annotation_count: int
    validation_annotation_count: int
    test_annotation_count: int
    error_count: int
    warning_count: int
    quality_summary: dict
    split_distribution: dict
    bbox_statistics: dict
    category_distribution: dict
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_utcnow)
    completed_at: Optional[datetime] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None
    error_message: Optional[str] = None

    def __post_init__(self) -> None:
        self.status = AnnotationQualityGateStatus(self.status)
        if self.error_count < 0 or self.warning_count < 0:
            raise ValueError("issue counts cannot be negative")
        if self.status == AnnotationQualityGateStatus.FAILED and self.error_count == 0:
            raise ValueError("failed quality gate requires at least one error")
        if self.status == AnnotationQualityGateStatus.PASSED and (self.error_count or self.warning_count):
            raise ValueError("passed quality gate cannot have errors or warnings")
        if self.status == AnnotationQualityGateStatus.WARNING and (self.error_count or self.warning_count == 0):
            raise ValueError("warning quality gate requires warnings and no errors")
        if self.is_passed != (self.status == AnnotationQualityGateStatus.PASSED):
            raise ValueError("is_passed must match passed status")
