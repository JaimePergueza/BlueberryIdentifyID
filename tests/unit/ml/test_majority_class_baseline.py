from uuid import uuid4

import pytest

from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.ml.training.majority_class_baseline import BaselineTrainingItem, MajorityClassBaselineTrainer


def _item(split: DatasetSplit, label: PredictedLabel) -> BaselineTrainingItem:
    return BaselineTrainingItem(
        dataset_split_item_id=uuid4(),
        dataset_item_id=uuid4(),
        split=split,
        ground_truth_label=label,
    )


def test_majority_class_uses_train_split_only_and_predicts_every_split():
    trainer = MajorityClassBaselineTrainer()
    items = [
        _item(DatasetSplit.TRAIN, PredictedLabel.SUSPICIOUS_GROWTH),
        _item(DatasetSplit.TRAIN, PredictedLabel.SUSPICIOUS_GROWTH),
        _item(DatasetSplit.TRAIN, PredictedLabel.NO_EVIDENT_GROWTH),
        _item(DatasetSplit.VALIDATION, PredictedLabel.NO_EVIDENT_GROWTH),
        _item(DatasetSplit.TEST, PredictedLabel.PROBABLE_FUNGAL_GROWTH),
    ]

    result = trainer.fit_predict(items)

    assert result.majority_label == PredictedLabel.SUSPICIOUS_GROWTH
    assert result.baseline_state["train_label_counts"] == {
        "no_evident_growth": 1,
        "suspicious_growth": 2,
    }
    assert [prediction.predicted_label for prediction in result.predictions] == [
        PredictedLabel.SUSPICIOUS_GROWTH
    ] * len(items)
    assert result.summary["uses_image_pixels"] is False
    assert result.metrics["accuracy_overall"] == 2 / 5
    assert result.metrics["accuracy_by_split"]["train"] == 2 / 3
    assert result.metrics["accuracy_by_split"]["validation"] == 0
    assert result.metrics["accuracy_by_split"]["test"] == 0
    assert result.metrics["support_by_split"] == {"test": 1, "train": 3, "validation": 1}
    assert result.metrics["confusion_matrix"]["suspicious_growth"] == {"suspicious_growth": 2}


def test_tie_break_is_prediction_label_enum_order():
    trainer = MajorityClassBaselineTrainer()
    items = [
        _item(DatasetSplit.TRAIN, PredictedLabel.SUSPICIOUS_GROWTH),
        _item(DatasetSplit.TRAIN, PredictedLabel.NO_EVIDENT_GROWTH),
        _item(DatasetSplit.VALIDATION, PredictedLabel.SUSPICIOUS_GROWTH),
        _item(DatasetSplit.TEST, PredictedLabel.NO_EVIDENT_GROWTH),
    ]

    result = trainer.fit_predict(items)

    assert result.majority_label == PredictedLabel.NO_EVIDENT_GROWTH
    assert result.baseline_state["tie_break_rule"] == "prediction_label_enum_order"


def test_requires_at_least_one_train_item():
    trainer = MajorityClassBaselineTrainer()

    with pytest.raises(ValueError, match="requires at least one train item"):
        trainer.fit_predict([_item(DatasetSplit.TEST, PredictedLabel.SUSPICIOUS_GROWTH)])
