from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from blueberry_microid.domain.enums.baseline_model_type import BaselineModelType
from blueberry_microid.domain.enums.comparison_primary_metric import ComparisonPrimaryMetric
from blueberry_microid.domain.enums.comparison_selection_policy import ComparisonSelectionPolicy
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.training_run_kind import TrainingRunKind


class CreateTrainingRunComparisonRequestBody(BaseModel):
    dataset_release_id: UUID
    training_run_ids: list[UUID]
    name: str
    description: Optional[str] = None
    primary_metric: ComparisonPrimaryMetric = ComparisonPrimaryMetric.ACCURACY
    primary_split: DatasetSplit = DatasetSplit.TEST
    selection_policy: ComparisonSelectionPolicy = ComparisonSelectionPolicy.BEST_PRIMARY_METRIC
    created_by: Optional[str] = None
    notes: Optional[str] = None


class TrainingRunComparisonEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    comparison_id: UUID
    training_run_id: UUID
    rank: Optional[int]
    run_kind: TrainingRunKind
    baseline_model_type: BaselineModelType
    primary_metric_value: Optional[float]
    train_accuracy: Optional[float]
    validation_accuracy: Optional[float]
    test_accuracy: Optional[float]
    generalization_gap: Optional[float]
    support_train: Optional[int]
    support_validation: Optional[int]
    support_test: Optional[int]
    metrics_snapshot: dict[str, Any]
    summary: dict[str, Any]
    created_at: datetime


class TrainingRunComparisonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_release_id: UUID
    name: str
    description: Optional[str]
    primary_metric: ComparisonPrimaryMetric
    primary_split: DatasetSplit
    selection_policy: ComparisonSelectionPolicy
    selected_training_run_id: Optional[UUID]
    comparison_summary: dict[str, Any]
    warnings: dict[str, Any]
    created_at: datetime
    created_by: Optional[str]
    notes: Optional[str]
    entries: list[TrainingRunComparisonEntryResponse] = []
