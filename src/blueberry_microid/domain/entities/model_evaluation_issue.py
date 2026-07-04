from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.model_evaluation_issue_severity import ModelEvaluationIssueSeverity


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ModelEvaluationIssue:
    model_evaluation_run_id: UUID
    severity: ModelEvaluationIssueSeverity
    code: str
    message: str
    id: UUID = field(default_factory=uuid4)
    details: Optional[dict] = None
    created_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        self.severity = ModelEvaluationIssueSeverity(self.severity)
        if not self.code:
            raise ValueError("code is required")
        if not self.message:
            raise ValueError("message is required")
