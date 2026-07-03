from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.predicted_label import PredictedLabel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class TrainingPrediction:
    training_run_id: UUID
    dataset_split_item_id: UUID
    dataset_item_id: UUID
    split: DatasetSplit
    ground_truth_label: PredictedLabel
    predicted_label: PredictedLabel
    is_correct: bool
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_utcnow)
