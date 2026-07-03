from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Optional

import numpy as np

from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.ml.configs.tabular_feature_training_config import TabularFeatureTrainingConfig
from blueberry_microid.ml.training.feature_matrix_builder import FeatureMatrix, FeatureMatrixItemRef

_LABEL_ORDER = [label.value for label in PredictedLabel]


@dataclass(frozen=True, slots=True)
class ClassicalTabularPredictionResult:
    dataset_split_item_id: object
    dataset_item_id: object
    split: DatasetSplit
    ground_truth_label: PredictedLabel
    predicted_label: PredictedLabel
    is_correct: bool


@dataclass(frozen=True, slots=True)
class ClassicalTabularBaselineResult:
    baseline_state: dict
    metrics: dict
    summary: dict
    predictions: list[ClassicalTabularPredictionResult]


class ClassicalTabularBaselineTrainer:
    """Classical LogisticRegression baseline over already-extracted features."""

    def fit_predict(
        self,
        matrix: FeatureMatrix,
        config: TabularFeatureTrainingConfig,
    ) -> ClassicalTabularBaselineResult:
        if len(matrix.y_train) < config.min_train_items:
            raise ValueError("classical tabular baseline requires more train items")
        train_classes = sorted({label.value for label in matrix.y_train}, key=_LABEL_ORDER.index)
        if len(train_classes) < config.min_classes_train:
            raise ValueError("classical tabular baseline requires at least two classes in train")

        LogisticRegression, StandardScaler = _load_sklearn()
        scaler = StandardScaler() if config.standardize_features else None
        X_train = scaler.fit_transform(matrix.X_train) if scaler is not None else matrix.X_train
        solver = config.solver or "liblinear"
        model = LogisticRegression(
            max_iter=config.max_iter,
            random_state=config.random_seed,
            solver=solver,
            class_weight=config.class_weight,
        )
        model.fit(X_train, [label.value for label in matrix.y_train])

        predictions = []
        for split, X, y, refs in (
            (DatasetSplit.TRAIN, matrix.X_train, matrix.y_train, matrix.train_refs),
            (DatasetSplit.VALIDATION, matrix.X_validation, matrix.y_validation, matrix.validation_refs),
            (DatasetSplit.TEST, matrix.X_test, matrix.y_test, matrix.test_refs),
        ):
            predictions.extend(self._predict_split(model, scaler, split, X, y, refs))

        metrics = _metrics(predictions)
        return ClassicalTabularBaselineResult(
            baseline_state={
                "feature_extraction_run_id": str(config.feature_extraction_run_id),
                "model_type": config.model_type.value,
                "feature_names": matrix.feature_names,
                "class_labels": sorted([str(label) for label in model.classes_], key=_LABEL_ORDER.index),
                "scaler_used": scaler is not None,
                "model_parameters": {
                    "max_iter": config.max_iter,
                    "solver": solver,
                    "class_weight": config.class_weight,
                    "random_seed": config.random_seed,
                },
                "train_item_count": len(matrix.y_train),
            },
            metrics=metrics,
            summary={
                "baseline_model_type": config.model_type.value,
                "uses_image_pixels": False,
                "uses_image_feature_vectors": True,
                "contains_deep_learning": False,
                "model_serialized": False,
                "prediction_count": len(predictions),
            },
            predictions=predictions,
        )

    def _predict_split(
        self,
        model,
        scaler,
        split: DatasetSplit,
        X: np.ndarray,
        y: list[PredictedLabel],
        refs: list[FeatureMatrixItemRef],
    ) -> list[ClassicalTabularPredictionResult]:
        if len(y) == 0:
            return []
        X_model = scaler.transform(X) if scaler is not None else X
        predicted_values = model.predict(X_model)
        return [
            ClassicalTabularPredictionResult(
                dataset_split_item_id=ref.dataset_split_item_id,
                dataset_item_id=ref.dataset_item_id,
                split=split,
                ground_truth_label=true_label,
                predicted_label=PredictedLabel(str(predicted_value)),
                is_correct=true_label.value == str(predicted_value),
            )
            for ref, true_label, predicted_value in zip(refs, y, predicted_values)
        ]


def _load_sklearn():
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:
        raise RuntimeError("scikit-learn is required for logistic_regression_tabular baseline") from exc
    return LogisticRegression, StandardScaler


def _metrics(predictions: list[ClassicalTabularPredictionResult]) -> dict:
    total = len(predictions)
    correct = sum(1 for prediction in predictions if prediction.is_correct)
    by_split: dict[str, list[ClassicalTabularPredictionResult]] = defaultdict(list)
    label_distribution: dict[str, Counter] = defaultdict(Counter)
    confusion: dict[str, Counter] = defaultdict(Counter)
    confusion_by_split: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))

    for prediction in predictions:
        split = prediction.split.value
        truth = prediction.ground_truth_label.value
        predicted = prediction.predicted_label.value
        by_split[split].append(prediction)
        label_distribution[split][truth] += 1
        confusion[truth][predicted] += 1
        confusion_by_split[split][truth][predicted] += 1

    return {
        "accuracy_overall": correct / total if total else 0.0,
        "accuracy_by_split": {
            split: _accuracy(split_predictions) for split, split_predictions in sorted(by_split.items())
        },
        "support_by_split": {split: len(split_predictions) for split, split_predictions in sorted(by_split.items())},
        "label_distribution_by_split": {
            split: dict(sorted(counts.items())) for split, counts in sorted(label_distribution.items())
        },
        "confusion_matrix": _counter_matrix(confusion),
        "confusion_matrix_by_split": {
            split: _counter_matrix(matrix) for split, matrix in sorted(confusion_by_split.items())
        },
    }


def _accuracy(predictions: list[ClassicalTabularPredictionResult]) -> float:
    return sum(1 for prediction in predictions if prediction.is_correct) / len(predictions) if predictions else 0.0


def _counter_matrix(matrix: dict[str, Counter]) -> dict[str, dict[str, int]]:
    return {truth: dict(sorted(preds.items())) for truth, preds in sorted(matrix.items())}
