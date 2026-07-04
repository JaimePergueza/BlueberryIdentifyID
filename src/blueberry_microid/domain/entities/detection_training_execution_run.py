from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.detection_training_execution_decision import DetectionTrainingExecutionDecision
from blueberry_microid.domain.enums.detection_training_execution_mode import DetectionTrainingExecutionMode
from blueberry_microid.domain.enums.detection_training_execution_status import DetectionTrainingExecutionStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DetectionTrainingExecutionRun:
    """A persisted execution-gate evaluation for a future, manually-triggered
    real training attempt.

    `status=ready_to_execute` never means training happened or a model was
    trained — only that every configured prerequisite gate passed and a
    human would still have to trigger a separate, future, out-of-band
    process. `is_executable` is always `False` in this phase: no code path
    exists yet that would let a `True` value mean anything, so the entity
    refuses to construct one that claims otherwise.
    """

    detection_training_run_id: UUID
    readiness_report_id: UUID
    environment_spec_id: UUID
    artifact_policy_id: UUID
    annotation_bundle_run_id: UUID
    dataset_release_id: UUID
    status: DetectionTrainingExecutionStatus
    decision: DetectionTrainingExecutionDecision
    mode: DetectionTrainingExecutionMode
    is_executable: bool
    config: dict
    prerequisite_summary: dict
    repository_safety_summary: dict
    execution_plan: dict
    command_preview: dict
    expected_outputs: dict
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
        self.status = DetectionTrainingExecutionStatus(self.status)
        self.decision = DetectionTrainingExecutionDecision(self.decision)
        self.mode = DetectionTrainingExecutionMode(self.mode)
        if self.error_count < 0 or self.warning_count < 0 or self.info_count < 0:
            raise ValueError("issue counts cannot be negative")
        if self.is_executable:
            raise ValueError(
                "is_executable must always be False in this phase; no real training executor exists yet"
            )
        if (
            self.status
            in {DetectionTrainingExecutionStatus.BLOCKED, DetectionTrainingExecutionStatus.FAILED}
            and self.error_count == 0
        ):
            raise ValueError("blocked/failed execution runs require at least one error")
        if (
            self.status
            not in {DetectionTrainingExecutionStatus.BLOCKED, DetectionTrainingExecutionStatus.FAILED}
            and self.error_count > 0
        ):
            raise ValueError("an execution run with blocking errors must be status blocked or failed")
