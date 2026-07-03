from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.detection_training_readiness_decision import DetectionTrainingReadinessDecision
from blueberry_microid.domain.enums.detection_training_readiness_status import DetectionTrainingReadinessStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DetectionTrainingReadinessReport:
    """A persisted verdict on whether a DetectionTrainingRun is technically
    ready to move to a future real training phase.

    `is_ready=true`/`decision=ready_for_training` only certifies technical
    readiness under the configured checks — never scientific sufficiency,
    never a trained model, never a confirmed colony/taxon. This report never
    trains anything and never touches image bytes or model weights.
    """

    detection_training_run_id: UUID
    annotation_bundle_run_id: UUID
    dataset_release_id: UUID
    petri_annotation_export_run_id: UUID
    decision: DetectionTrainingReadinessDecision
    status: DetectionTrainingReadinessStatus
    is_ready: bool
    config: dict
    data_summary: dict
    split_summary: dict
    quality_summary: dict
    environment_summary: dict
    contract_summary: dict
    risk_summary: dict
    recommendation_summary: dict
    error_count: int
    warning_count: int
    info_count: int
    id: UUID = field(default_factory=uuid4)
    annotation_quality_gate_run_id: Optional[UUID] = None
    created_at: datetime = field(default_factory=_utcnow)
    completed_at: Optional[datetime] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None
    error_message: Optional[str] = None

    def __post_init__(self) -> None:
        self.decision = DetectionTrainingReadinessDecision(self.decision)
        self.status = DetectionTrainingReadinessStatus(self.status)
        if self.error_count < 0 or self.warning_count < 0 or self.info_count < 0:
            raise ValueError("issue counts cannot be negative")
        if self.status == DetectionTrainingReadinessStatus.READY and self.error_count > 0:
            raise ValueError("ready readiness reports cannot have blocking errors")
        if self.status == DetectionTrainingReadinessStatus.BLOCKED and self.error_count == 0:
            raise ValueError("blocked readiness reports require at least one error")
        if self.status == DetectionTrainingReadinessStatus.READY and not self.is_ready:
            raise ValueError("ready readiness reports must be is_ready=true")
        if (
            self.status in {DetectionTrainingReadinessStatus.BLOCKED, DetectionTrainingReadinessStatus.FAILED}
            and self.is_ready
        ):
            raise ValueError("blocked/failed readiness reports must be is_ready=false")
        if self.is_ready and self.decision != DetectionTrainingReadinessDecision.READY_FOR_TRAINING:
            raise ValueError("is_ready=true requires decision=ready_for_training")
