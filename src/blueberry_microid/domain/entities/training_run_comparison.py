from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.comparison_primary_metric import ComparisonPrimaryMetric
from blueberry_microid.domain.enums.comparison_selection_policy import ComparisonSelectionPolicy
from blueberry_microid.domain.enums.dataset_split import DatasetSplit


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class TrainingRunComparison:
    dataset_release_id: UUID
    name: str
    primary_metric: ComparisonPrimaryMetric
    primary_split: DatasetSplit
    selection_policy: ComparisonSelectionPolicy
    comparison_summary: dict
    id: UUID = field(default_factory=uuid4)
    description: Optional[str] = None
    selected_training_run_id: Optional[UUID] = None
    warnings: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utcnow)
    created_by: Optional[str] = None
    notes: Optional[str] = None
