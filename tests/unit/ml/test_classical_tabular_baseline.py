from uuid import uuid4

import numpy as np
import pytest

from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.ml.configs.tabular_feature_training_config import TabularFeatureTrainingConfig
from blueberry_microid.ml.training.classical_tabular_baseline import ClassicalTabularBaselineTrainer
from blueberry_microid.ml.training.feature_matrix_builder import FeatureMatrix, FeatureMatrixItemRef


def _ref(split: DatasetSplit) -> FeatureMatrixItemRef:
    return FeatureMatrixItemRef(dataset_split_item_id=uuid4(), dataset_item_id=uuid4(), split=split)


def _config(**overrides) -> TabularFeatureTrainingConfig:
    return TabularFeatureTrainingConfig(feature_extraction_run_id=uuid4(), **overrides)


def _matrix() -> FeatureMatrix:
    return FeatureMatrix(
        X_train=np.asarray([[0.0], [0.1], [5.0], [5.1]], dtype=float),
        y_train=[
            PredictedLabel.NO_EVIDENT_GROWTH,
            PredictedLabel.NO_EVIDENT_GROWTH,
            PredictedLabel.SUSPICIOUS_GROWTH,
            PredictedLabel.SUSPICIOUS_GROWTH,
        ],
        X_validation=np.asarray([[0.2], [5.2]], dtype=float),
        y_validation=[PredictedLabel.NO_EVIDENT_GROWTH, PredictedLabel.SUSPICIOUS_GROWTH],
        X_test=np.asarray([[0.3], [5.3]], dtype=float),
        y_test=[PredictedLabel.NO_EVIDENT_GROWTH, PredictedLabel.SUSPICIOUS_GROWTH],
        feature_names=["petri__intensity__mean_intensity"],
        train_refs=[_ref(DatasetSplit.TRAIN) for _ in range(4)],
        validation_refs=[_ref(DatasetSplit.VALIDATION) for _ in range(2)],
        test_refs=[_ref(DatasetSplit.TEST) for _ in range(2)],
    )


def test_trains_with_two_classes_and_generates_predictions_for_all_splits():
    result = ClassicalTabularBaselineTrainer().fit_predict(_matrix(), _config(random_seed=7))

    assert result.summary["uses_image_feature_vectors"] is True
    assert result.summary["uses_image_pixels"] is False
    assert result.baseline_state["model_type"] == "logistic_regression_tabular"
    assert result.baseline_state["feature_names"] == ["petri__intensity__mean_intensity"]
    assert len(result.predictions) == 8
    assert {prediction.split for prediction in result.predictions} == {
        DatasetSplit.TRAIN,
        DatasetSplit.VALIDATION,
        DatasetSplit.TEST,
    }


def test_fails_with_one_train_class_or_too_few_train_items():
    one_class = _matrix()
    one_class = FeatureMatrix(
        X_train=one_class.X_train[:2],
        y_train=[PredictedLabel.NO_EVIDENT_GROWTH, PredictedLabel.NO_EVIDENT_GROWTH],
        X_validation=one_class.X_validation,
        y_validation=one_class.y_validation,
        X_test=one_class.X_test,
        y_test=one_class.y_test,
        feature_names=one_class.feature_names,
        train_refs=one_class.train_refs[:2],
        validation_refs=one_class.validation_refs,
        test_refs=one_class.test_refs,
    )

    with pytest.raises(ValueError, match="at least two classes"):
        ClassicalTabularBaselineTrainer().fit_predict(one_class, _config())

    with pytest.raises(ValueError, match="more train items"):
        ClassicalTabularBaselineTrainer().fit_predict(_matrix(), _config(min_train_items=5))


def test_metrics_are_real_and_do_not_include_precision_recall_or_f1():
    result = ClassicalTabularBaselineTrainer().fit_predict(_matrix(), _config())

    assert result.metrics["accuracy_overall"] == 1.0
    assert result.metrics["accuracy_by_split"]["train"] == 1.0
    assert result.metrics["confusion_matrix"]["no_evident_growth"]["no_evident_growth"] == 4
    assert "confusion_matrix_by_split" in result.metrics
    assert "precision" not in result.metrics
    assert "recall" not in result.metrics
    assert "f1" not in result.metrics


def test_result_is_deterministic_with_random_seed():
    trainer = ClassicalTabularBaselineTrainer()
    first = trainer.fit_predict(_matrix(), _config(random_seed=42))
    second = trainer.fit_predict(_matrix(), _config(random_seed=42))

    assert [p.predicted_label for p in first.predictions] == [p.predicted_label for p in second.predictions]
