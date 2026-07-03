from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.detection_training_environment_decision import (
    DetectionTrainingEnvironmentDecision,
)
from blueberry_microid.domain.enums.detection_training_environment_status import DetectionTrainingEnvironmentStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DetectionTrainingEnvironmentSpec:
    """A persisted specification/evaluation of the environment a future real
    training attempt would run in.

    `is_environment_ready=true`/`decision=environment_ready` only certifies
    that the configured technical checks passed — never that a real training
    environment was provisioned, never that ultralytics/torch were installed,
    and never that training was executed. This entity never triggers an
    install, download, or training action.
    """

    detection_training_run_id: UUID
    readiness_report_id: UUID
    annotation_bundle_run_id: UUID
    dataset_release_id: UUID
    decision: DetectionTrainingEnvironmentDecision
    status: DetectionTrainingEnvironmentStatus
    is_environment_ready: bool
    config: dict
    detected_environment: dict
    dependency_policy: dict
    hardware_policy: dict
    artifact_policy: dict
    execution_policy: dict
    setup_instructions: dict
    safe_check_summary: dict
    risk_summary: dict
    recommendation_summary: dict
    error_count: int
    warning_count: int
    info_count: int
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_utcnow)
    completed_at: Optional[datetime] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None
    error_message: Optional[str] = None

    def __post_init__(self) -> None:
        self.decision = DetectionTrainingEnvironmentDecision(self.decision)
        self.status = DetectionTrainingEnvironmentStatus(self.status)
        if self.error_count < 0 or self.warning_count < 0 or self.info_count < 0:
            raise ValueError("issue counts cannot be negative")
        if self.status == DetectionTrainingEnvironmentStatus.READY and self.error_count > 0:
            raise ValueError("ready environment specs cannot have blocking errors")
        if self.status == DetectionTrainingEnvironmentStatus.BLOCKED and self.error_count == 0:
            raise ValueError("blocked environment specs require at least one error")
        if self.status == DetectionTrainingEnvironmentStatus.READY and not self.is_environment_ready:
            raise ValueError("ready environment specs must be is_environment_ready=true")
        if (
            self.status in {DetectionTrainingEnvironmentStatus.BLOCKED, DetectionTrainingEnvironmentStatus.FAILED}
            and self.is_environment_ready
        ):
            raise ValueError("blocked/failed environment specs must be is_environment_ready=false")
        if self.is_environment_ready and self.decision != DetectionTrainingEnvironmentDecision.ENVIRONMENT_READY:
            raise ValueError("is_environment_ready=true requires decision=environment_ready")
