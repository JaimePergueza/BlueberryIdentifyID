from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from uuid import UUID

from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.predicted_label import PredictedLabel

_LABEL_ORDER = [label.value for label in PredictedLabel]


@dataclass(frozen=True, slots=True)
class BaselineTrainingItem:
    dataset_split_item_id: UUID
    dataset_item_id: UUID
    split: DatasetSplit
    ground_truth_label: PredictedLabel


@dataclass(frozen=True, slots=True)
class BaselinePredictionResult:
    dataset_split_item_id: UUID
    dataset_item_id: UUID
    split: DatasetSplit
    ground_truth_label: PredictedLabel
    predicted_label: PredictedLabel
    is_correct: bool


@dataclass(frozen=True, slots=True)
class MajorityClassBaselineResult:
    majority_label: PredictedLabel
    baseline_state: dict
    metrics: dict
    summary: dict
    predictions: list[BaselinePredictionResult]


class MajorityClassBaselineTrainer:
    """Non-deep baseline using only train labels to choose one class."""

    def fit_predict(self, items: list[BaselineTrainingItem]) -> MajorityClassBaselineResult:
        train_items = [item for item in items if item.split == DatasetSplit.TRAIN]
        if not train_items:
            raise ValueError("majority_class baseline requires at least one train item")

        train_counts = Counter(item.ground_truth_label.value for item in train_items)
        max_count = max(train_counts.values())
        tied = [label for label, count in train_counts.items() if count == max_count]
        majority_label_value = sorted(tied, key=lambda label: _LABEL_ORDER.index(label))[0]
        majority_label = PredictedLabel(majority_label_value)

        predictions = [
            BaselinePredictionResult(
                dataset_split_item_id=item.dataset_split_item_id,
                dataset_item_id=item.dataset_item_id,
                split=item.split,
                ground_truth_label=item.ground_truth_label,
                predicted_label=majority_label,
                is_correct=item.ground_truth_label == majority_label,
            )
            for item in items
        ]
        metrics = _metrics(predictions)
        return MajorityClassBaselineResult(
            majority_label=majority_label,
            baseline_state={
                "majority_label": majority_label.value,
                "train_label_counts": dict(sorted(train_counts.items())),
                "tie_break_rule": "prediction_label_enum_order",
            },
            metrics=metrics,
            summary={
                "baseline_model_type": "majority_class",
                "uses_image_pixels": False,
                "train_items_used_for_majority_label": len(train_items),
                "prediction_count": len(predictions),
            },
            predictions=predictions,
        )


def _metrics(predictions: list[BaselinePredictionResult]) -> dict:
    total = len(predictions)
    correct = sum(1 for prediction in predictions if prediction.is_correct)
    by_split: dict[str, list[BaselinePredictionResult]] = defaultdict(list)
    label_distribution: dict[str, Counter] = defaultdict(Counter)
    confusion: dict[str, Counter] = defaultdict(Counter)
    for prediction in predictions:
        split = prediction.split.value
        by_split[split].append(prediction)
        label_distribution[split][prediction.ground_truth_label.value] += 1
        confusion[prediction.ground_truth_label.value][prediction.predicted_label.value] += 1

    return {
        "accuracy_overall": correct / total if total else 0.0,
        "accuracy_by_split": {
            split: (sum(1 for prediction in split_predictions if prediction.is_correct) / len(split_predictions))
            for split, split_predictions in sorted(by_split.items())
        },
        "support_by_split": {split: len(split_predictions) for split, split_predictions in sorted(by_split.items())},
        "label_distribution_by_split": {
            split: dict(sorted(counts.items())) for split, counts in sorted(label_distribution.items())
        },
        "confusion_matrix": {truth: dict(sorted(preds.items())) for truth, preds in sorted(confusion.items())},
    }
