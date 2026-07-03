from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.detection_training_algorithm import DetectionTrainingAlgorithm
from blueberry_microid.domain.enums.detection_training_mode import DetectionTrainingMode
from blueberry_microid.domain.enums.detection_training_status import DetectionTrainingStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DetectionTrainingRun:
    """A persisted dry-run plan for a future object-detection training attempt.

    This entity never represents a trained model: `status=planned` means a
    valid, reproducible plan was produced from an already-passed annotation
    quality gate, not that any weights exist. No image bytes, model weights,
    or taxonomy are ever stored here — only JSON planning metadata.
    """

    annotation_bundle_run_id: UUID
    dataset_release_id: UUID
    petri_annotation_export_run_id: UUID
    algorithm: DetectionTrainingAlgorithm
    mode: DetectionTrainingMode
    status: DetectionTrainingStatus
    is_runnable: bool
    config: dict
    training_plan: dict
    command_preview: dict
    dataset_summary: dict
    quality_gate_summary: dict
    expected_outputs: dict
    issue_count: int
    warning_count: int
    error_count: int
    id: UUID = field(default_factory=uuid4)
    annotation_quality_gate_run_id: Optional[UUID] = None
    created_at: datetime = field(default_factory=_utcnow)
    completed_at: Optional[datetime] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None
    error_message: Optional[str] = None

    def __post_init__(self) -> None:
        self.algorithm = DetectionTrainingAlgorithm(self.algorithm)
        self.mode = DetectionTrainingMode(self.mode)
        self.status = DetectionTrainingStatus(self.status)
        if self.error_count < 0 or self.warning_count < 0 or self.issue_count < 0:
            raise ValueError("issue counts cannot be negative")
        if self.status == DetectionTrainingStatus.PLANNED and self.error_count > 0:
            raise ValueError("planned detection training runs cannot have blocking errors")
        if self.status == DetectionTrainingStatus.BLOCKED and self.error_count == 0:
            raise ValueError("blocked detection training runs require at least one error")
        if self.status == DetectionTrainingStatus.PLANNED and not self.is_runnable:
            raise ValueError("planned detection training runs must be is_runnable=true")
        if self.status in {DetectionTrainingStatus.BLOCKED, DetectionTrainingStatus.FAILED} and self.is_runnable:
            raise ValueError("blocked/failed detection training runs must be is_runnable=false")
