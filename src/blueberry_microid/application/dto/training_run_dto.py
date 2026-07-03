from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.training_prediction import TrainingPrediction
from blueberry_microid.domain.entities.training_run import TrainingRun
from blueberry_microid.domain.enums.baseline_model_type import BaselineModelType
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.training_run_kind import TrainingRunKind
from blueberry_microid.domain.enums.training_run_status import TrainingRunStatus
from blueberry_microid.ml.configs.training_config import TrainingConfig


@dataclass(frozen=True, slots=True)
class CreateBaselineTrainingRunRequest:
    dataset_release_id: UUID
    preflight_run_id: UUID
    experiment_name: str
    training_config: TrainingConfig
    baseline_model_type: BaselineModelType = BaselineModelType.MAJORITY_CLASS
    created_by: Optional[str] = None
    notes: Optional[str] = None


@dataclass(frozen=True, slots=True)
class TrainingRunDTO:
    id: UUID
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
    completed_at: Optional[datetime]
    created_at: datetime
    created_by: Optional[str]
    notes: Optional[str]
    error_message: Optional[str]

    @classmethod
    def from_entity(cls, run: TrainingRun) -> "TrainingRunDTO":
        return cls(**run.__dict__)


@dataclass(frozen=True, slots=True)
class TrainingPredictionDTO:
    id: UUID
    training_run_id: UUID
    dataset_split_item_id: UUID
    dataset_item_id: UUID
    split: DatasetSplit
    ground_truth_label: PredictedLabel
    predicted_label: PredictedLabel
    is_correct: bool
    created_at: datetime

    @classmethod
    def from_entity(cls, prediction: TrainingPrediction) -> "TrainingPredictionDTO":
        return cls(**prediction.__dict__)


def training_config_to_dict(training_config: TrainingConfig) -> dict:
    return asdict(training_config)
