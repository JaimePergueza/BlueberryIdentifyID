from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.detection_training_readiness_issue_severity import (
    DetectionTrainingReadinessIssueSeverity,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class DetectionTrainingReadinessIssue:
    """One finding from evaluating a DetectionTrainingRun's readiness.

    Never stores model weights, images, complete label sets, or binaries —
    only short metadata about a readiness check.
    """

    readiness_report_id: UUID
    severity: DetectionTrainingReadinessIssueSeverity
    code: str
    message: str
    id: UUID = field(default_factory=uuid4)
    details: Optional[dict] = None
    created_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        DetectionTrainingReadinessIssueSeverity(self.severity)
        if not self.code:
            raise ValueError("code must not be blank")
        if not self.message:
            raise ValueError("message must not be blank")
