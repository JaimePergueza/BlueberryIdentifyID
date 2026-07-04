from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.detection_training_artifact_policy_decision import (
    DetectionTrainingArtifactPolicyDecision,
)
from blueberry_microid.domain.enums.detection_training_artifact_policy_status import (
    DetectionTrainingArtifactPolicyStatus,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DetectionTrainingArtifactPolicy:
    """A persisted policy/registry of artifacts a future real training
    attempt would produce for a DetectionTrainingRun.

    `is_policy_ready=true`/`decision=artifact_policy_ready` only certifies
    that the configured technical checks passed — never that a real weight,
    metric, or prediction file exists. This entity never creates artifact
    files and never stores binary content.
    """

    detection_training_run_id: UUID
    readiness_report_id: UUID
    environment_spec_id: UUID
    annotation_bundle_run_id: UUID
    dataset_release_id: UUID
    decision: DetectionTrainingArtifactPolicyDecision
    status: DetectionTrainingArtifactPolicyStatus
    is_policy_ready: bool
    config: dict
    planned_output_summary: dict
    storage_policy: dict
    git_policy: dict
    checksum_policy: dict
    registry_summary: dict
    risk_summary: dict
    recommendation_summary: dict
    error_count: int
    warning_count: int
    info_count: int
    id: UUID = field(default_factory=uuid4)
    artifact_root_dir: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)
    completed_at: Optional[datetime] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None
    error_message: Optional[str] = None

    def __post_init__(self) -> None:
        self.decision = DetectionTrainingArtifactPolicyDecision(self.decision)
        self.status = DetectionTrainingArtifactPolicyStatus(self.status)
        if self.error_count < 0 or self.warning_count < 0 or self.info_count < 0:
            raise ValueError("issue counts cannot be negative")
        if self.status == DetectionTrainingArtifactPolicyStatus.READY and self.error_count > 0:
            raise ValueError("ready artifact policies cannot have blocking errors")
        if self.status == DetectionTrainingArtifactPolicyStatus.BLOCKED and self.error_count == 0:
            raise ValueError("blocked artifact policies require at least one error")
        if self.status == DetectionTrainingArtifactPolicyStatus.READY and not self.is_policy_ready:
            raise ValueError("ready artifact policies must be is_policy_ready=true")
        if (
            self.status
            in {DetectionTrainingArtifactPolicyStatus.BLOCKED, DetectionTrainingArtifactPolicyStatus.FAILED}
            and self.is_policy_ready
        ):
            raise ValueError("blocked/failed artifact policies must be is_policy_ready=false")
        if (
            self.is_policy_ready
            and self.decision != DetectionTrainingArtifactPolicyDecision.ARTIFACT_POLICY_READY
        ):
            raise ValueError("is_policy_ready=true requires decision=artifact_policy_ready")
