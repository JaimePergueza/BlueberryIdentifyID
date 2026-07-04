from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.detection_training_artifact_issue_severity import (
    DetectionTrainingArtifactIssueSeverity,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class DetectionTrainingArtifactIssue:
    """One finding from evaluating a DetectionTrainingArtifactPolicy.

    Never stores model weights, images, complete label sets, or binaries —
    only short metadata about an artifact-policy check.
    """

    artifact_policy_id: UUID
    severity: DetectionTrainingArtifactIssueSeverity
    code: str
    message: str
    id: UUID = field(default_factory=uuid4)
    artifact_path: Optional[str] = None
    details: Optional[dict] = None
    created_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        DetectionTrainingArtifactIssueSeverity(self.severity)
        if not self.code:
            raise ValueError("code must not be blank")
        if not self.message:
            raise ValueError("message must not be blank")
