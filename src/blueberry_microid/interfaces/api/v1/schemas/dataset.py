from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision
from blueberry_microid.domain.enums.split_strategy import SplitStrategy


class DatasetSnapshotCreate(BaseModel):
    name: str
    version: str
    description: Optional[str] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None
    include_inconclusive: bool = False
    include_rejected: bool = False


class DatasetSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    version: str
    description: Optional[str]
    created_at: datetime
    created_by: Optional[str]
    selection_criteria: Optional[dict[str, Any]]
    item_count: int
    label_distribution: Optional[dict[str, int]]
    notes: Optional[str]


class DatasetItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_snapshot_id: UUID
    analysis_run_id: UUID
    sample_id: UUID
    petri_image_id: UUID
    micro_image_id: UUID
    prediction_id: UUID
    final_review_id: UUID
    ground_truth_label: Optional[PredictedLabel]
    source_review_decision: ReviewDecision
    included: bool
    exclusion_reason: Optional[str]
    created_at: datetime


class DatasetReleaseCreate(BaseModel):
    dataset_snapshot_id: UUID
    name: str
    version: str
    split_strategy: SplitStrategy = SplitStrategy.BY_SAMPLE
    random_seed: int = 42
    train_ratio: float = 0.70
    validation_ratio: float = 0.15
    test_ratio: float = 0.15
    created_by: Optional[str] = None
    notes: Optional[str] = None


class DatasetReleaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_snapshot_id: UUID
    name: str
    version: str
    split_strategy: SplitStrategy
    random_seed: int
    train_ratio: float
    validation_ratio: float
    test_ratio: float
    item_count: int
    train_count: int
    validation_count: int
    test_count: int
    label_distribution: Optional[dict[str, int]]
    split_distribution: Optional[dict[str, dict[str, int]]]
    created_at: datetime
    created_by: Optional[str]
    notes: Optional[str]


class DatasetSplitItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_release_id: UUID
    dataset_item_id: UUID
    sample_id: UUID
    split: DatasetSplit
    ground_truth_label: Optional[PredictedLabel]
    created_at: datetime

