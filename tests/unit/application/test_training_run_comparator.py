from datetime import datetime, timezone
from uuid import uuid4

import pytest

from blueberry_microid.application.exceptions import TrainingRunComparisonNotAllowedError
from blueberry_microid.application.services.training_run_comparator import TrainingRunComparator
from blueberry_microid.domain.entities.training_run import TrainingRun
from blueberry_microid.domain.enums.baseline_model_type import BaselineModelType
from blueberry_microid.domain.enums.comparison_primary_metric import ComparisonPrimaryMetric
from blueberry_microid.domain.enums.comparison_selection_policy import ComparisonSelectionPolicy
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.training_run_kind import TrainingRunKind
from blueberry_microid.domain.enums.training_run_status import TrainingRunStatus


def _run(
    *,
    dataset_release_id=None,
    model_type=BaselineModelType.MAJORITY_CLASS,
    status=TrainingRunStatus.COMPLETED,
    validation_accuracy=0.5,
    test_accuracy=0.5,
    support_validation=2,
    support_test=2,
    metrics: dict | None = None,
) -> TrainingRun:
    release_id = dataset_release_id or uuid4()
    return TrainingRun(
        dataset_release_id=release_id,
        preflight_run_id=uuid4(),
        run_kind=TrainingRunKind.BASELINE,
        baseline_model_type=model_type,
        status=status,
        experiment_name=f"{model_type.value}-unit",
        config={},
        baseline_state={"feature_extraction_run_id": str(uuid4())}
        if model_type == BaselineModelType.LOGISTIC_REGRESSION_TABULAR
        else {},
        metrics=metrics
        if metrics is not None
        else {
            "accuracy_by_split": {
                "train": 0.9,
                "validation": validation_accuracy,
                "test": test_accuracy,
            },
            "support_by_split": {
                "train": 4,
                "validation": support_validation,
                "test": support_test,
            },
        },
        summary={},
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )


def _compare(runs, split=DatasetSplit.TEST, policy=ComparisonSelectionPolicy.BEST_PRIMARY_METRIC):
    return TrainingRunComparator().compare(runs, ComparisonPrimaryMetric.ACCURACY, split, policy)


def test_compares_completed_runs_from_same_release_and_extracts_metrics():
    release_id = uuid4()
    majority = _run(dataset_release_id=release_id, validation_accuracy=0.6, test_accuracy=0.5)
    classical = _run(
        dataset_release_id=release_id,
        model_type=BaselineModelType.LOGISTIC_REGRESSION_TABULAR,
        validation_accuracy=0.7,
        test_accuracy=0.75,
    )

    result = _compare([majority, classical])

    assert result.entries[0].training_run_id == classical.id
    assert result.entries[0].primary_metric_value == 0.75
    assert result.entries[0].support_test == 2
    assert result.entries[0].generalization_gap == pytest.approx(0.15)
    assert result.selected_training_run_id == classical.id
    assert result.summary["contains_deep_learning"] is False


def test_rejects_runs_from_different_releases_or_not_completed():
    with pytest.raises(TrainingRunComparisonNotAllowedError, match="same dataset_release"):
        _compare([_run(), _run()])

    release_id = uuid4()
    with pytest.raises(TrainingRunComparisonNotAllowedError, match="completed"):
        _compare([_run(dataset_release_id=release_id), _run(dataset_release_id=release_id, status=TrainingRunStatus.FAILED)])


def test_rejects_missing_metrics_without_inventing_values():
    release_id = uuid4()
    missing_metrics = _run(dataset_release_id=release_id, metrics={})

    with pytest.raises(TrainingRunComparisonNotAllowedError, match="no metrics"):
        _compare([missing_metrics, _run(dataset_release_id=release_id)])

    missing_accuracy = _run(dataset_release_id=release_id, metrics={"support_by_split": {"test": 2}})
    with pytest.raises(TrainingRunComparisonNotAllowedError, match="accuracy_by_split"):
        _compare([missing_accuracy, _run(dataset_release_id=release_id)])


def test_ranking_and_selection_policies_are_deterministic():
    release_id = uuid4()
    majority = _run(dataset_release_id=release_id, model_type=BaselineModelType.MAJORITY_CLASS, test_accuracy=0.7)
    classical = _run(
        dataset_release_id=release_id,
        model_type=BaselineModelType.LOGISTIC_REGRESSION_TABULAR,
        test_accuracy=0.7,
    )

    best_metric = _compare([classical, majority], policy=ComparisonSelectionPolicy.BEST_PRIMARY_METRIC)
    no_selection = _compare([classical, majority], policy=ComparisonSelectionPolicy.NO_AUTO_SELECTION)
    prefer_simple = _compare([classical, majority], policy=ComparisonSelectionPolicy.PREFER_SIMPLER_IF_TIE)

    assert [entry.rank for entry in best_metric.entries] == [1, 2]
    assert best_metric.selected_training_run_id == sorted([majority.id, classical.id], key=str)[0]
    assert no_selection.selected_training_run_id is None
    assert prefer_simple.entries[0].training_run_id == majority.id
    assert prefer_simple.selected_training_run_id == majority.id


def test_validation_split_gap_and_low_support_warning():
    release_id = uuid4()
    majority = _run(dataset_release_id=release_id, validation_accuracy=0.4, support_validation=1)
    classical = _run(
        dataset_release_id=release_id,
        model_type=BaselineModelType.LOGISTIC_REGRESSION_TABULAR,
        validation_accuracy=0.6,
        support_validation=1,
    )

    result = _compare([majority, classical], split=DatasetSplit.VALIDATION)

    assert result.entries[0].primary_metric_value == 0.6
    assert result.entries[0].generalization_gap == pytest.approx(0.3)
    assert len(result.warnings["low_support"]) == 2
