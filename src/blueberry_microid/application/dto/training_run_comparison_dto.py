from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.training_run_comparison import TrainingRunComparison
from blueberry_microid.domain.entities.training_run_comparison_entry import TrainingRunComparisonEntry
from blueberry_microid.domain.enums.baseline_model_type import BaselineModelType
from blueberry_microid.domain.enums.comparison_primary_metric import ComparisonPrimaryMetric
from blueberry_microid.domain.enums.comparison_selection_policy import ComparisonSelectionPolicy
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.training_run_kind import TrainingRunKind


@dataclass(frozen=True, slots=True)
class CreateTrainingRunComparisonRequest:
    dataset_release_id: UUID
    training_run_ids: list[UUID]
    name: str
    description: Optional[str] = None
    primary_metric: ComparisonPrimaryMetric = ComparisonPrimaryMetric.ACCURACY
    primary_split: DatasetSplit = DatasetSplit.TEST
    selection_policy: ComparisonSelectionPolicy = ComparisonSelectionPolicy.BEST_PRIMARY_METRIC
    created_by: Optional[str] = None
    notes: Optional[str] = None


@dataclass(frozen=True, slots=True)
class TrainingRunComparisonEntryDTO:
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
    metrics_snapshot: dict
    summary: dict
    created_at: datetime

    @classmethod
    def from_entity(cls, entry: TrainingRunComparisonEntry) -> "TrainingRunComparisonEntryDTO":
        return cls(**entry.__dict__)


@dataclass(frozen=True, slots=True)
class TrainingRunComparisonDTO:
    id: UUID
    dataset_release_id: UUID
    name: str
    description: Optional[str]
    primary_metric: ComparisonPrimaryMetric
    primary_split: DatasetSplit
    selection_policy: ComparisonSelectionPolicy
    selected_training_run_id: Optional[UUID]
    comparison_summary: dict
    warnings: dict
    created_at: datetime
    created_by: Optional[str]
    notes: Optional[str]
    entries: list[TrainingRunComparisonEntryDTO]

    @classmethod
    def from_entity(
        cls,
        comparison: TrainingRunComparison,
        entries: list[TrainingRunComparisonEntry] | None = None,
    ) -> "TrainingRunComparisonDTO":
        return cls(
            id=comparison.id,
            dataset_release_id=comparison.dataset_release_id,
            name=comparison.name,
            description=comparison.description,
            primary_metric=comparison.primary_metric,
            primary_split=comparison.primary_split,
            selection_policy=comparison.selection_policy,
            selected_training_run_id=comparison.selected_training_run_id,
            comparison_summary=comparison.comparison_summary,
            warnings=comparison.warnings,
            created_at=comparison.created_at,
            created_by=comparison.created_by,
            notes=comparison.notes,
            entries=[TrainingRunComparisonEntryDTO.from_entity(entry) for entry in (entries or [])],
        )
