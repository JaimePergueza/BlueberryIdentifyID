from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.baseline_model_type import BaselineModelType
from blueberry_microid.domain.enums.training_run_kind import TrainingRunKind
from blueberry_microid.domain.enums.training_run_status import TrainingRunStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class TrainingRun:
    dataset_release_id: UUID
    preflight_run_id: UUID
    run_kind: TrainingRunKind
    baseline_model_type: BaselineModelType
    status: TrainingRunStatus
    experiment_name: str
    config: dict
    baseline_state: dict
    metrics: dict
    summary: dict
    started_at: datetime
    id: UUID = field(default_factory=uuid4)
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=_utcnow)
    created_by: Optional[str] = None
    notes: Optional[str] = None
    error_message: Optional[str] = None
