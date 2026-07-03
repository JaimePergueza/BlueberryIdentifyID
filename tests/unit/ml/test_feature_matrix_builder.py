from uuid import uuid4

import pytest

from blueberry_microid.domain.entities.dataset_split_item import DatasetSplitItem
from blueberry_microid.domain.entities.image_feature_vector import ImageFeatureVector
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.image_modality import ImageModality
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.ml.configs.tabular_feature_training_config import TabularFeatureTrainingConfig
from blueberry_microid.ml.training.feature_matrix_builder import FeatureMatrixBuilder


def _split_item(split: DatasetSplit, label: PredictedLabel) -> DatasetSplitItem:
    return DatasetSplitItem(
        dataset_release_id=uuid4(),
        dataset_item_id=uuid4(),
        sample_id=uuid4(),
        split=split,
        ground_truth_label=label,
    )


def _vector(split_item: DatasetSplitItem, modality: ImageModality, features: dict | None = None) -> ImageFeatureVector:
    return ImageFeatureVector(
        feature_extraction_run_id=uuid4(),
        dataset_release_id=split_item.dataset_release_id,
        dataset_item_id=split_item.dataset_item_id,
        dataset_split_item_id=split_item.id,
        split=split_item.split,
        modality=modality,
        image_path=f"/tmp/{modality.value}.png",
        features=features
        or {
            "intensity": {"mean_intensity": 12.0, "ignored_text": "x"},
            "histogram": {"grayscale_histogram": [0.25, 0.75], "bins": 2},
        },
        preprocessing={},
        extraction_version="v1",
    )


def _config(**overrides) -> TabularFeatureTrainingConfig:
    data = {"feature_extraction_run_id": uuid4(), **overrides}
    return TabularFeatureTrainingConfig(**data)


def test_builds_petri_only_matrix_with_numeric_features_and_histograms():
    item = _split_item(DatasetSplit.TRAIN, PredictedLabel.SUSPICIOUS_GROWTH)

    matrix = FeatureMatrixBuilder().build([_vector(item, ImageModality.PETRI)], [item], _config(fusion_strategy="petri_only"))

    assert matrix.X_train.shape == (1, 4)
    assert matrix.y_train == [PredictedLabel.SUSPICIOUS_GROWTH]
    assert matrix.feature_names == [
        "petri__histogram__bins",
        "petri__histogram__grayscale_histogram__00",
        "petri__histogram__grayscale_histogram__01",
        "petri__intensity__mean_intensity",
    ]
    assert "petri__intensity__ignored_text" not in matrix.feature_names


def test_builds_micro_only_matrix():
    item = _split_item(DatasetSplit.TRAIN, PredictedLabel.NO_EVIDENT_GROWTH)

    matrix = FeatureMatrixBuilder().build([_vector(item, ImageModality.MICRO)], [item], _config(fusion_strategy="micro_only"))

    assert matrix.X_train.shape[0] == 1
    assert all(name.startswith("micro__") for name in matrix.feature_names)


def test_builds_concatenated_matrix_with_deterministic_feature_order_and_splits():
    train = _split_item(DatasetSplit.TRAIN, PredictedLabel.SUSPICIOUS_GROWTH)
    validation = _split_item(DatasetSplit.VALIDATION, PredictedLabel.NO_EVIDENT_GROWTH)
    vectors = [
        _vector(train, ImageModality.MICRO, {"z": 2.0}),
        _vector(train, ImageModality.PETRI, {"a": 1.0}),
        _vector(validation, ImageModality.MICRO, {"z": 4.0}),
        _vector(validation, ImageModality.PETRI, {"a": 3.0}),
    ]

    matrix = FeatureMatrixBuilder().build(vectors, [validation, train], _config())

    assert matrix.feature_names == ["micro__z", "petri__a"]
    assert matrix.X_train.tolist() == [[2.0, 1.0]]
    assert matrix.X_validation.tolist() == [[4.0, 3.0]]
    assert matrix.train_refs[0].dataset_split_item_id == train.id
    assert matrix.validation_refs[0].dataset_split_item_id == validation.id


def test_fails_when_required_modality_is_missing():
    item = _split_item(DatasetSplit.TRAIN, PredictedLabel.SUSPICIOUS_GROWTH)

    with pytest.raises(ValueError, match="missing micro features"):
        FeatureMatrixBuilder().build([_vector(item, ImageModality.PETRI)], [item], _config())


def test_excludes_inconclusive_by_default_and_includes_when_allowed():
    inconclusive = _split_item(DatasetSplit.TRAIN, PredictedLabel.INCONCLUSIVE)
    usable = _split_item(DatasetSplit.TRAIN, PredictedLabel.SUSPICIOUS_GROWTH)
    vectors = [
        _vector(inconclusive, ImageModality.PETRI),
        _vector(inconclusive, ImageModality.MICRO),
        _vector(usable, ImageModality.PETRI),
        _vector(usable, ImageModality.MICRO),
    ]

    default_matrix = FeatureMatrixBuilder().build(vectors, [inconclusive, usable], _config())
    include_matrix = FeatureMatrixBuilder().build(
        vectors, [inconclusive, usable], _config(allow_inconclusive=True)
    )

    assert default_matrix.y_train == [PredictedLabel.SUSPICIOUS_GROWTH]
    assert sorted(label.value for label in include_matrix.y_train) == sorted(
        [PredictedLabel.INCONCLUSIVE.value, PredictedLabel.SUSPICIOUS_GROWTH.value]
    )
