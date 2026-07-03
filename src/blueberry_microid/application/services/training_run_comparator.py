from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from blueberry_microid.application.exceptions import TrainingRunComparisonNotAllowedError
from blueberry_microid.domain.entities.training_run import TrainingRun
from blueberry_microid.domain.enums.baseline_model_type import BaselineModelType
from blueberry_microid.domain.enums.comparison_primary_metric import ComparisonPrimaryMetric
from blueberry_microid.domain.enums.comparison_selection_policy import ComparisonSelectionPolicy
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.training_run_kind import TrainingRunKind
from blueberry_microid.domain.enums.training_run_status import TrainingRunStatus

_MODEL_SIMPLICITY_ORDER = {
    BaselineModelType.MAJORITY_CLASS: 0,
    BaselineModelType.LOGISTIC_REGRESSION_TABULAR: 1,
}
_LOW_SUPPORT_THRESHOLD = 2


@dataclass(frozen=True, slots=True)
class ComparisonEntryResult:
    training_run_id: UUID
    rank: int
    run_kind: TrainingRunKind
    baseline_model_type: BaselineModelType
    primary_metric_value: float
    train_accuracy: float | None
    validation_accuracy: float | None
    test_accuracy: float | None
    generalization_gap: float | None
    support_train: int | None
    support_validation: int | None
    support_test: int | None
    metrics_snapshot: dict
    summary: dict


@dataclass(frozen=True, slots=True)
class TrainingRunComparisonResult:
    entries: list[ComparisonEntryResult]
    selected_training_run_id: UUID | None
    warnings: dict
    summary: dict


class TrainingRunComparator:
    """Compares persisted TrainingRun metrics without training anything."""

    def compare(
        self,
        training_runs: list[TrainingRun],
        primary_metric: ComparisonPrimaryMetric,
        primary_split: DatasetSplit,
        selection_policy: ComparisonSelectionPolicy,
    ) -> TrainingRunComparisonResult:
        if primary_metric != ComparisonPrimaryMetric.ACCURACY:
            raise TrainingRunComparisonNotAllowedError("only accuracy comparison is supported")
        if primary_split not in {DatasetSplit.VALIDATION, DatasetSplit.TEST}:
            raise TrainingRunComparisonNotAllowedError("primary_split must be validation or test")
        if len(training_runs) < 2:
            raise TrainingRunComparisonNotAllowedError("at least two training runs are required")

        dataset_release_ids = {run.dataset_release_id for run in training_runs}
        if len(dataset_release_ids) != 1:
            raise TrainingRunComparisonNotAllowedError("training runs must belong to the same dataset_release")
        not_completed = [run.id for run in training_runs if run.status != TrainingRunStatus.COMPLETED]
        if not_completed:
            raise TrainingRunComparisonNotAllowedError("only completed training runs can be compared")

        warnings: dict[str, list[dict]] = {"low_support": []}
        raw_entries = [self._entry_for_run(run, primary_split, warnings) for run in training_runs]
        ranked_entries = _rank_entries(raw_entries, selection_policy)
        selected_training_run_id = _select_training_run(ranked_entries, selection_policy)

        warnings = {key: value for key, value in warnings.items() if value}
        return TrainingRunComparisonResult(
            entries=ranked_entries,
            selected_training_run_id=selected_training_run_id,
            warnings=warnings,
            summary={
                "primary_metric": primary_metric.value,
                "primary_split": primary_split.value,
                "selection_policy": selection_policy.value,
                "training_run_count": len(training_runs),
                "selected_training_run_id": str(selected_training_run_id) if selected_training_run_id else None,
                "ranking": [
                    {
                        "rank": entry.rank,
                        "training_run_id": str(entry.training_run_id),
                        "baseline_model_type": entry.baseline_model_type.value,
                        "primary_metric_value": entry.primary_metric_value,
                    }
                    for entry in ranked_entries
                ],
                "contains_deep_learning": False,
                "selection_is_preliminary": True,
            },
        )

    def _entry_for_run(
        self,
        run: TrainingRun,
        primary_split: DatasetSplit,
        warnings: dict[str, list[dict]],
    ) -> ComparisonEntryResult:
        if not run.metrics:
            raise TrainingRunComparisonNotAllowedError(f"training_run '{run.id}' has no metrics")
        accuracy_by_split = run.metrics.get("accuracy_by_split")
        support_by_split = run.metrics.get("support_by_split")
        if not isinstance(accuracy_by_split, dict):
            raise TrainingRunComparisonNotAllowedError(f"training_run '{run.id}' has no accuracy_by_split metrics")
        if not isinstance(support_by_split, dict):
            raise TrainingRunComparisonNotAllowedError(f"training_run '{run.id}' has no support_by_split metrics")

        train_accuracy = _optional_float(accuracy_by_split.get(DatasetSplit.TRAIN.value))
        validation_accuracy = _optional_float(accuracy_by_split.get(DatasetSplit.VALIDATION.value))
        test_accuracy = _optional_float(accuracy_by_split.get(DatasetSplit.TEST.value))
        primary_metric_value = _optional_float(accuracy_by_split.get(primary_split.value))
        if primary_metric_value is None:
            raise TrainingRunComparisonNotAllowedError(
                f"training_run '{run.id}' is missing accuracy for split '{primary_split.value}'"
            )

        support_train = _optional_int(support_by_split.get(DatasetSplit.TRAIN.value))
        support_validation = _optional_int(support_by_split.get(DatasetSplit.VALIDATION.value))
        support_test = _optional_int(support_by_split.get(DatasetSplit.TEST.value))
        primary_support = _optional_int(support_by_split.get(primary_split.value))
        if primary_support is None:
            raise TrainingRunComparisonNotAllowedError(
                f"training_run '{run.id}' is missing support for split '{primary_split.value}'"
            )
        if primary_support < _LOW_SUPPORT_THRESHOLD:
            warnings["low_support"].append(
                {
                    "training_run_id": str(run.id),
                    "split": primary_split.value,
                    "support": primary_support,
                    "message": "primary split support is low; interpret comparison cautiously",
                }
            )

        comparison_accuracy = validation_accuracy if primary_split == DatasetSplit.VALIDATION else test_accuracy
        generalization_gap = None
        if train_accuracy is not None and comparison_accuracy is not None:
            generalization_gap = train_accuracy - comparison_accuracy

        return ComparisonEntryResult(
            training_run_id=run.id,
            rank=0,
            run_kind=run.run_kind,
            baseline_model_type=run.baseline_model_type,
            primary_metric_value=primary_metric_value,
            train_accuracy=train_accuracy,
            validation_accuracy=validation_accuracy,
            test_accuracy=test_accuracy,
            generalization_gap=generalization_gap,
            support_train=support_train,
            support_validation=support_validation,
            support_test=support_test,
            metrics_snapshot=run.metrics,
            summary={
                "experiment_name": run.experiment_name,
                "baseline_model_type": run.baseline_model_type.value,
                "feature_extraction_run_id": run.baseline_state.get("feature_extraction_run_id")
                if isinstance(run.baseline_state, dict)
                else None,
                "selection_is_preliminary": True,
            },
        )


def _rank_entries(
    entries: list[ComparisonEntryResult],
    selection_policy: ComparisonSelectionPolicy,
) -> list[ComparisonEntryResult]:
    ranked = sorted(
        entries,
        key=lambda entry: (
            -entry.primary_metric_value,
            _tie_break_model_order(entry, selection_policy),
            str(entry.training_run_id),
        ),
    )
    return [
        ComparisonEntryResult(
            training_run_id=entry.training_run_id,
            rank=index,
            run_kind=entry.run_kind,
            baseline_model_type=entry.baseline_model_type,
            primary_metric_value=entry.primary_metric_value,
            train_accuracy=entry.train_accuracy,
            validation_accuracy=entry.validation_accuracy,
            test_accuracy=entry.test_accuracy,
            generalization_gap=entry.generalization_gap,
            support_train=entry.support_train,
            support_validation=entry.support_validation,
            support_test=entry.support_test,
            metrics_snapshot=entry.metrics_snapshot,
            summary=entry.summary,
        )
        for index, entry in enumerate(ranked, start=1)
    ]


def _select_training_run(
    ranked_entries: list[ComparisonEntryResult],
    selection_policy: ComparisonSelectionPolicy,
) -> UUID | None:
    if selection_policy == ComparisonSelectionPolicy.NO_AUTO_SELECTION:
        return None
    return ranked_entries[0].training_run_id if ranked_entries else None


def _tie_break_model_order(
    entry: ComparisonEntryResult,
    selection_policy: ComparisonSelectionPolicy,
) -> int:
    if selection_policy == ComparisonSelectionPolicy.PREFER_SIMPLER_IF_TIE:
        return _MODEL_SIMPLICITY_ORDER.get(entry.baseline_model_type, 99)
    return 0


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value
