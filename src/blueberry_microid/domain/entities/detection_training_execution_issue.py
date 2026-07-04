from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.detection_training_execution_issue_severity import (
    DetectionTrainingExecutionIssueSeverity,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class DetectionTrainingExecutionIssue:
    """One finding from evaluating a DetectionTrainingExecutionRun.

    Never stores model weights, images, complete label sets, or binaries —
    only short metadata about an execution-gate check.
    """

    execution_run_id: UUID
    severity: DetectionTrainingExecutionIssueSeverity
    code: str
    message: str
    id: UUID = field(default_factory=uuid4)
    details: Optional[dict] = None
    created_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        DetectionTrainingExecutionIssueSeverity(self.severity)
        if not self.code:
            raise ValueError("code must not be blank")
        if not self.message:
            raise ValueError("message must not be blank")
