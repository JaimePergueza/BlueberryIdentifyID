from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from blueberry_microid.domain.enums.baseline_model_type import BaselineModelType
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.training_run_kind import TrainingRunKind
from blueberry_microid.domain.enums.training_run_status import TrainingRunStatus
from blueberry_microid.interfaces.api.v1.schemas.ml_preflight import TrainingConfigRequest


class CreateBaselineTrainingRunRequestBody(BaseModel):
    dataset_release_id: UUID
    preflight_run_id: UUID
    experiment_name: str
    training_config: TrainingConfigRequest
    baseline_model_type: BaselineModelType = BaselineModelType.MAJORITY_CLASS
    created_by: Optional[str] = None
    notes: Optional[str] = None


class TrainingRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_release_id: UUID
    preflight_run_id: UUID
    run_kind: TrainingRunKind
    baseline_model_type: BaselineModelType
    status: TrainingRunStatus
    experiment_name: str
    config: dict[str, Any]
    baseline_state: dict[str, Any]
    metrics: dict[str, Any]
    summary: dict[str, Any]
    started_at: datetime
    completed_at: Optional[datetime]
    created_at: datetime
    created_by: Optional[str]
    notes: Optional[str]
    error_message: Optional[str]


class TrainingPredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    training_run_id: UUID
    dataset_split_item_id: UUID
    dataset_item_id: UUID
    split: DatasetSplit
    ground_truth_label: PredictedLabel
    predicted_label: PredictedLabel
    is_correct: bool
    created_at: datetime
