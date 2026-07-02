from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.predicted_label import PredictedLabel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class DatasetSplitItem:
    """One DatasetItem's train/validation/test assignment within a specific
    DatasetRelease. `sample_id` is denormalized from the DatasetItem purely
    so leakage audits (and the manifest export) never need an extra join to
    prove which Sample an assignment belongs to."""

    dataset_release_id: UUID
    dataset_item_id: UUID
    sample_id: UUID
    split: DatasetSplit
    id: UUID = field(default_factory=uuid4)
    ground_truth_label: Optional[PredictedLabel] = None
    created_at: datetime = field(default_factory=_utcnow)
