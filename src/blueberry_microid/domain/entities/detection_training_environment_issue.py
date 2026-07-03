from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.detection_training_environment_issue_severity import (
    DetectionTrainingEnvironmentIssueSeverity,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class DetectionTrainingEnvironmentIssue:
    """One finding from evaluating a DetectionTrainingEnvironmentSpec.

    Never stores model weights, images, complete label sets, or binaries —
    only short metadata about an environment check.
    """

    environment_spec_id: UUID
    severity: DetectionTrainingEnvironmentIssueSeverity
    code: str
    message: str
    id: UUID = field(default_factory=uuid4)
    details: Optional[dict] = None
    created_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        DetectionTrainingEnvironmentIssueSeverity(self.severity)
        if not self.code:
            raise ValueError("code must not be blank")
        if not self.message:
            raise ValueError("message must not be blank")
