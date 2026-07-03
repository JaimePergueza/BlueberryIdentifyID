from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.training_preflight_issue_severity import TrainingPreflightIssueSeverity


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class TrainingPreflightIssue:
    """A persisted validation error or warning for a preflight run."""

    preflight_run_id: UUID
    severity: TrainingPreflightIssueSeverity
    code: str
    message: str
    id: UUID = dataclass_field(default_factory=uuid4)
    field: Optional[str] = None
    item_ref: Optional[str] = None
    created_at: datetime = dataclass_field(default_factory=_utcnow)
