import os
import sys

import pytest
from PIL import Image

from blueberry_microid.domain.enums.image_feature_extraction_status import ImageFeatureExtractionStatus
from blueberry_microid.domain.enums.image_modality import ImageModality
from blueberry_microid.ml.configs.image_feature_extraction_config import ImageFeatureExtractionConfig
from blueberry_microid.ml.contracts.training_manifest import TrainingManifest, TrainingManifestItem
from blueberry_microid.ml.preprocessing.image_feature_extractor import ImageFeatureExtractor


def _write_image(path, *, width=64, height=64, color="blue", fmt="JPEG", mode="RGB"):
    Image.new(mode, (width, height), color=color).save(str(path), format=fmt)
    return os.path.getsize(str(path))


def _make_item(index, tmp_path, *, petri_path=None, micro_path=None, _skip_petri_write=False, _skip_micro_write=False, **overrides):
    petri_path = petri_path if petri_path is not None else str(tmp_path / f"petri-{index}.jpg")
    micro_path = micro_path if micro_path is not None else str(tmp_path / f"micro-{index}.png")

    if petri_path and not _skip_petri_write and not os.path.exists(petri_path):
        _write_image(petri_path, fmt="JPEG")
    if micro_path and not _skip_micro_write and not os.path.exists(micro_path):
        _write_image(micro_path, fmt="PNG", mode="L", color=100)

    data = {
        "split": "train",
        "analysis_run_id": f"run-{index}",
        "sample_id": f"sample-{index}",
        "sample_code": f"S-{index}",
        "dataset_item_id": f"11111111-1111-1111-1111-{index:012d}",
        "dataset_split_item_id": f"22222222-2222-2222-2222-{index:012d}",
        "petri_image_path": petri_path,
        "micro_image_path": micro_path,
        "ground_truth_label": "suspicious_growth",
        "prediction_label": "suspicious_growth",
        "source_review_decision": "confirmed",
        "final_review_id": f"review-{index}",
    }
    data.update(overrides)
    return TrainingManifestItem(**data)


def _manifest(items):
    return TrainingManifest(
        dataset_release_id="release-1",
        dataset_snapshot_id="snapshot-1",
        name="release",
        version="0.1.0",
        split_strategy="by_sample",
        random_seed=42,
        train_ratio=1.0,
        validation_ratio=0.0,
        test_ratio=0.0,
        item_count=len(items),
        train_count=len(items),
        validation_count=0,
        test_count=0,
        items=items,
    )


def _vectors_by_modality(report, modality):
    return [v for v in report.vectors if v.modality == modality]


def test_valid_rgb_image_produces_expected_features(tmp_path):
    item = _make_item(1, tmp_path)
    report = ImageFeatureExtractor().extract(_manifest([item]), ImageFeatureExtractionConfig())

    assert report.status == ImageFeatureExtractionStatus.COMPLETED
    petri_vector = _vectors_by_modality(report, ImageModality.PETRI)[0]
    assert set(petri_vector.features.keys()) == {
        "geometry",
        "intensity",
        "color",
        "sharpness",
        "texture",
        "histogram",
    }
    assert "mean_r" in petri_vector.features["color"]


def test_grayscale_image_produces_expected_features(tmp_path):
    gray_path = tmp_path / "petri-gray.jpg"
    _write_image(gray_path, mode="L", color=90, fmt="JPEG")
    item = _make_item(1, tmp_path, petri_path=str(gray_path), _skip_petri_write=True)
    config = ImageFeatureExtractionConfig(convert_to_rgb=False)

    report = ImageFeatureExtractor().extract(_manifest([item]), config)

    petri_vector = _vectors_by_modality(report, ImageModality.PETRI)[0]
    assert "color" not in petri_vector.features
    assert "intensity" in petri_vector.features
    assert petri_vector.preprocessing["processed_mode"] == "L"


def test_histogram_is_normalized_to_approximately_one(tmp_path):
    item = _make_item(1, tmp_path)
    report = ImageFeatureExtractor().extract(_manifest([item]), ImageFeatureExtractionConfig())

    petri_vector = _vectors_by_modality(report, ImageModality.PETRI)[0]
    histogram = petri_vector.features["histogram"]["grayscale_histogram"]
    assert len(histogram) == 16
    assert sum(histogram) == pytest.approx(1.0, abs=1e-4)


def test_geometry_features_are_correct(tmp_path):
    petri_path = tmp_path / "petri-1.jpg"
    _write_image(petri_path, width=120, height=60, fmt="JPEG")
    item = _make_item(1, tmp_path, petri_path=str(petri_path), _skip_petri_write=True)

    report = ImageFeatureExtractor().extract(_manifest([item]), ImageFeatureExtractionConfig())

    geometry = _vectors_by_modality(report, ImageModality.PETRI)[0].features["geometry"]
    assert geometry["width"] == 120
    assert geometry["height"] == 60
    assert geometry["aspect_ratio"] == 2.0
    assert geometry["file_size_bytes"] == os.path.getsize(petri_path)


def test_intensity_features_are_correct_for_constant_image(tmp_path):
    petri_path = tmp_path / "petri-const.jpg"
    _write_image(petri_path, color=(150, 150, 150), fmt="JPEG")
    item = _make_item(1, tmp_path, petri_path=str(petri_path), _skip_petri_write=True)

    report = ImageFeatureExtractor().extract(_manifest([item]), ImageFeatureExtractionConfig())

    intensity = _vectors_by_modality(report, ImageModality.PETRI)[0].features["intensity"]
    assert intensity["mean_intensity"] == 150.0
    assert intensity["std_intensity"] == 0.0
    assert intensity["min_intensity"] == 150.0
    assert intensity["max_intensity"] == 150.0


def test_bright_and_dark_pixel_ratios_are_calculated(tmp_path):
    dark_path = tmp_path / "petri-dark.jpg"
    bright_path = tmp_path / "micro-bright.png"
    _write_image(dark_path, color=(10, 10, 10), fmt="JPEG")
    _write_image(bright_path, color=(250, 250, 250), fmt="PNG")
    item = _make_item(
        1, tmp_path, petri_path=str(dark_path), micro_path=str(bright_path), _skip_petri_write=True, _skip_micro_write=True
    )

    report = ImageFeatureExtractor().extract(_manifest([item]), ImageFeatureExtractionConfig())

    petri_texture = _vectors_by_modality(report, ImageModality.PETRI)[0].features["texture"]
    micro_texture = _vectors_by_modality(report, ImageModality.MICRO)[0].features["texture"]
    assert petri_texture["dark_pixel_ratio"] == 1.0
    assert petri_texture["bright_pixel_ratio"] == 0.0
    assert micro_texture["bright_pixel_ratio"] == 1.0
    assert micro_texture["dark_pixel_ratio"] == 0.0


def test_sharpness_feature_is_deterministic(tmp_path):
    item = _make_item(1, tmp_path)
    manifest = _manifest([item])
    config = ImageFeatureExtractionConfig()

    report_a = ImageFeatureExtractor().extract(manifest, config)
    report_b = ImageFeatureExtractor().extract(manifest, config)

    sharpness_a = _vectors_by_modality(report_a, ImageModality.PETRI)[0].features["sharpness"]
    sharpness_b = _vectors_by_modality(report_b, ImageModality.PETRI)[0].features["sharpness"]
    assert sharpness_a == sharpness_b


def test_petri_and_micro_produce_separate_vectors(tmp_path):
    item = _make_item(1, tmp_path)
    report = ImageFeatureExtractor().extract(_manifest([item]), ImageFeatureExtractionConfig())

    assert len(report.vectors) == 2
    modalities = {v.modality for v in report.vectors}
    assert modalities == {ImageModality.PETRI, ImageModality.MICRO}
    assert report.petri_feature_count == 1
    assert report.micro_feature_count == 1


def test_missing_image_fails_in_a_controlled_way(tmp_path):
    item = _make_item(1, tmp_path, petri_path=str(tmp_path / "missing.jpg"), _skip_petri_write=True)

    report = ImageFeatureExtractor().extract(_manifest([item]), ImageFeatureExtractionConfig())

    assert report.status == ImageFeatureExtractionStatus.FAILED
    assert any(e.modality == ImageModality.PETRI for e in report.errors)
    assert len(_vectors_by_modality(report, ImageModality.PETRI)) == 0


def test_corrupted_image_fails_in_a_controlled_way(tmp_path):
    corrupted_path = tmp_path / "corrupted.jpg"
    corrupted_path.write_bytes(b"not a real image")
    item = _make_item(1, tmp_path, petri_path=str(corrupted_path), _skip_petri_write=True)

    report = ImageFeatureExtractor().extract(_manifest([item]), ImageFeatureExtractionConfig())

    assert report.status == ImageFeatureExtractionStatus.FAILED
    assert any("corrupted" in e.message for e in report.errors)


def test_resize_enabled_changes_reported_preprocessing(tmp_path):
    item = _make_item(1, tmp_path)
    manifest = _manifest([item])

    default_report = ImageFeatureExtractor().extract(manifest, ImageFeatureExtractionConfig())
    resized_report = ImageFeatureExtractor().extract(
        manifest, ImageFeatureExtractionConfig(resize_enabled=True, resize_width=10, resize_height=10)
    )

    default_preprocessing = _vectors_by_modality(default_report, ImageModality.PETRI)[0].preprocessing
    resized_preprocessing = _vectors_by_modality(resized_report, ImageModality.PETRI)[0].preprocessing
    assert default_preprocessing["resize_applied"] is False
    assert resized_preprocessing["resize_applied"] is True
    assert resized_preprocessing["processed_width"] == 10
    assert resized_preprocessing["processed_height"] == 10
    assert resized_preprocessing["original_width"] == 64


def test_does_not_modify_original_file(tmp_path):
    item = _make_item(1, tmp_path)
    petri_bytes_before = (tmp_path / "petri-1.jpg").read_bytes()

    ImageFeatureExtractor().extract(_manifest([item]), ImageFeatureExtractionConfig())

    assert (tmp_path / "petri-1.jpg").read_bytes() == petri_bytes_before


def test_result_is_deterministic(tmp_path):
    item = _make_item(1, tmp_path)
    manifest = _manifest([item])
    config = ImageFeatureExtractionConfig()

    report_a = ImageFeatureExtractor().extract(manifest, config)
    report_b = ImageFeatureExtractor().extract(manifest, config)

    features_a = [v.features for v in report_a.vectors]
    features_b = [v.features for v in report_b.vectors]
    assert features_a == features_b


def test_does_not_store_large_arrays_in_features(tmp_path):
    item = _make_item(1, tmp_path)
    report = ImageFeatureExtractor().extract(_manifest([item]), ImageFeatureExtractionConfig())

    petri_vector = _vectors_by_modality(report, ImageModality.PETRI)[0]
    histogram = petri_vector.features["histogram"]["grayscale_histogram"]
    assert len(histogram) <= 64
    for value in petri_vector.features.values():
        assert isinstance(value, dict)


def test_does_not_require_pytorch(tmp_path):
    item = _make_item(1, tmp_path)
    ImageFeatureExtractor().extract(_manifest([item]), ImageFeatureExtractionConfig())

    assert "torch" not in sys.modules
    assert "tensorflow" not in sys.modules


def test_does_not_compute_classification_metrics(tmp_path):
    item = _make_item(1, tmp_path)
    report = ImageFeatureExtractor().extract(_manifest([item]), ImageFeatureExtractionConfig())

    haystack = str(report.summary).lower()
    for forbidden in ("accuracy", "precision", "recall", "f1_score", "confusion_matrix"):
        assert forbidden not in haystack
