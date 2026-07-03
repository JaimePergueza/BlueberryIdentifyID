from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.baseline_model_type import BaselineModelType
from blueberry_microid.domain.enums.training_run_kind import TrainingRunKind


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class TrainingRunComparisonEntry:
    comparison_id: UUID
    training_run_id: UUID
    run_kind: TrainingRunKind
    baseline_model_type: BaselineModelType
    metrics_snapshot: dict
    summary: dict
    id: UUID = field(default_factory=uuid4)
    rank: Optional[int] = None
    primary_metric_value: Optional[float] = None
    train_accuracy: Optional[float] = None
    validation_accuracy: Optional[float] = None
    test_accuracy: Optional[float] = None
    generalization_gap: Optional[float] = None
    support_train: Optional[int] = None
    support_validation: Optional[int] = None
    support_test: Optional[int] = None
    created_at: datetime = field(default_factory=_utcnow)
