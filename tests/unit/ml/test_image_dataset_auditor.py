import os
import sys
from io import BytesIO

import pytest
from PIL import Image

from blueberry_microid.domain.enums.image_dataset_audit_issue_severity import ImageDatasetAuditIssueSeverity
from blueberry_microid.domain.enums.image_dataset_audit_status import ImageDatasetAuditStatus
from blueberry_microid.domain.enums.image_modality import ImageModality
from blueberry_microid.ml.configs.image_audit_config import ImageAuditConfig
from blueberry_microid.ml.contracts.training_manifest import TrainingManifest, TrainingManifestItem
from blueberry_microid.ml.validation.image_dataset_auditor import ImageDatasetAuditor

_ERROR = ImageDatasetAuditIssueSeverity.ERROR
_WARNING = ImageDatasetAuditIssueSeverity.WARNING


def _write_image(path, *, width=100, height=100, color="blue", fmt="JPEG", mode="RGB"):
    image = Image.new(mode, (width, height), color=color if mode != "CMYK" else (0, 0, 0, 0))
    image.save(str(path), format=fmt)
    return os.path.getsize(str(path))


def _make_item(index, tmp_path, *, petri_path=None, micro_path=None, **overrides):
    petri_path = petri_path if petri_path is not None else str(tmp_path / f"petri-{index}.jpg")
    micro_path = micro_path if micro_path is not None else str(tmp_path / f"micro-{index}.png")

    skip_petri_write = overrides.get("_skip_petri_write", False)
    skip_micro_write = overrides.get("_skip_micro_write", False)
    if petri_path and not skip_petri_write and not os.path.exists(petri_path):
        _write_image(petri_path, fmt="JPEG")
    if micro_path and not skip_micro_write and not os.path.exists(micro_path):
        _write_image(micro_path, fmt="PNG")

    petri_size = os.path.getsize(petri_path) if petri_path and os.path.exists(petri_path) else None
    micro_size = os.path.getsize(micro_path) if micro_path and os.path.exists(micro_path) else None

    data = {
        "split": "train",
        "analysis_run_id": f"run-{index}",
        "sample_id": f"sample-{index}",
        "sample_code": f"S-{index}",
        "dataset_item_id": f"11111111-1111-1111-1111-{index:012d}",
        "dataset_split_item_id": f"22222222-2222-2222-2222-{index:012d}",
        "petri_image_path": petri_path,
        "micro_image_path": micro_path,
        "petri_width": 100,
        "petri_height": 100,
        "petri_file_size_bytes": petri_size,
        "micro_width": 100,
        "micro_height": 100,
        "micro_file_size_bytes": micro_size,
        "ground_truth_label": "suspicious_growth",
        "prediction_label": "suspicious_growth",
        "source_review_decision": "confirmed",
        "final_review_id": f"review-{index}",
    }
    for key in ("_skip_petri_write", "_skip_micro_write"):
        overrides.pop(key, None)
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


def test_valid_images_produce_passed_status(tmp_path):
    item = _make_item(1, tmp_path)
    report = ImageDatasetAuditor().audit(_manifest([item]), ImageAuditConfig())

    assert report.status == ImageDatasetAuditStatus.PASSED
    assert report.is_passed is True
    assert report.error_count == 0
    assert report.warning_count == 0


def test_missing_petri_image_produces_error(tmp_path):
    item = _make_item(1, tmp_path, petri_path=str(tmp_path / "does-not-exist.jpg"), _skip_petri_write=True)
    report = ImageDatasetAuditor().audit(_manifest([item]), ImageAuditConfig())

    assert report.status == ImageDatasetAuditStatus.FAILED
    codes = [f.code for f in report.errors]
    assert "image_missing" in codes
    assert all(f.modality == ImageModality.PETRI for f in report.errors if f.code == "image_missing")


def test_missing_micro_image_produces_error(tmp_path):
    item = _make_item(1, tmp_path, micro_path=str(tmp_path / "does-not-exist.png"), _skip_micro_write=True)
    report = ImageDatasetAuditor().audit(_manifest([item]), ImageAuditConfig())

    assert report.status == ImageDatasetAuditStatus.FAILED
    micro_errors = [f for f in report.errors if f.code == "image_missing" and f.modality == ImageModality.MICRO]
    assert len(micro_errors) == 1


def test_empty_path_produces_error(tmp_path):
    item = _make_item(1, tmp_path, petri_path="", _skip_petri_write=True)
    report = ImageDatasetAuditor().audit(_manifest([item]), ImageAuditConfig())

    assert report.status == ImageDatasetAuditStatus.FAILED
    assert any(f.code == "image_empty_path" and f.modality == ImageModality.PETRI for f in report.errors)


def test_corrupted_file_produces_error(tmp_path):
    corrupted_path = tmp_path / "corrupted.jpg"
    corrupted_path.write_bytes(b"not a real image, just garbage bytes")
    item = _make_item(1, tmp_path, petri_path=str(corrupted_path), _skip_petri_write=True)

    report = ImageDatasetAuditor().audit(_manifest([item]), ImageAuditConfig())

    assert report.status == ImageDatasetAuditStatus.FAILED
    assert any(f.code == "image_unreadable" and f.modality == ImageModality.PETRI for f in report.errors)


def test_disallowed_format_produces_error_by_design(tmp_path):
    gif_path = tmp_path / "petri.gif"
    Image.new("RGB", (100, 100), color="blue").save(str(gif_path), format="GIF")
    item = _make_item(1, tmp_path, petri_path=str(gif_path), _skip_petri_write=True)

    report = ImageDatasetAuditor().audit(_manifest([item]), ImageAuditConfig())

    assert any(f.code == "image_format_mismatch" and f.severity == _ERROR for f in report.errors)
    assert report.status == ImageDatasetAuditStatus.FAILED


def test_image_smaller_than_minimum_produces_warning_by_design(tmp_path):
    small_path = tmp_path / "small.jpg"
    _write_image(small_path, width=10, height=10, fmt="JPEG")
    item = _make_item(1, tmp_path, petri_path=str(small_path), petri_width=10, petri_height=10, _skip_petri_write=True)

    report = ImageDatasetAuditor().audit(_manifest([item]), ImageAuditConfig())

    assert report.error_count == 0
    assert any(f.code == "image_too_small" and f.severity == _WARNING for f in report.warnings)
    assert report.status == ImageDatasetAuditStatus.WARNING


def test_unsupported_color_mode_produces_warning_by_design(tmp_path):
    cmyk_path = tmp_path / "cmyk.jpg"
    Image.new("CMYK", (100, 100)).save(str(cmyk_path), format="JPEG")
    item = _make_item(1, tmp_path, petri_path=str(cmyk_path), _skip_petri_write=True)

    report = ImageDatasetAuditor().audit(_manifest([item]), ImageAuditConfig())

    assert report.error_count == 0
    assert any(f.code == "image_unsupported_color_mode" and f.severity == _WARNING for f in report.warnings)
    assert report.status == ImageDatasetAuditStatus.WARNING


def test_duplicate_path_produces_warning(tmp_path):
    shared_path = str(tmp_path / "shared-petri.jpg")
    _write_image(shared_path, fmt="JPEG")
    item1 = _make_item(1, tmp_path, petri_path=shared_path, _skip_petri_write=True)
    item2 = _make_item(2, tmp_path, petri_path=shared_path, _skip_petri_write=True)

    report = ImageDatasetAuditor().audit(_manifest([item1, item2]), ImageAuditConfig())

    assert any(f.code == "image_duplicate_path" for f in report.warnings)


def test_format_distribution_is_calculated_correctly(tmp_path):
    item1 = _make_item(1, tmp_path)
    item2 = _make_item(2, tmp_path)
    report = ImageDatasetAuditor().audit(_manifest([item1, item2]), ImageAuditConfig())

    assert report.format_distribution.get("JPEG") == 2
    assert report.format_distribution.get("PNG") == 2


def test_color_mode_distribution_is_calculated_correctly(tmp_path):
    item = _make_item(1, tmp_path)
    report = ImageDatasetAuditor().audit(_manifest([item]), ImageAuditConfig())

    assert report.color_mode_distribution.get("RGB") == 2


def test_dimension_distribution_is_calculated_correctly(tmp_path):
    item = _make_item(1, tmp_path)
    report = ImageDatasetAuditor().audit(_manifest([item]), ImageAuditConfig())

    assert report.dimension_distribution.get("under_256") == 2


def test_file_size_distribution_is_calculated_correctly(tmp_path):
    item = _make_item(1, tmp_path)
    report = ImageDatasetAuditor().audit(_manifest([item]), ImageAuditConfig())

    assert sum(report.file_size_distribution.values()) == 2
    assert report.file_size_distribution.get("under_100kb") == 2


def test_differentiates_petri_and_micro_modality(tmp_path):
    item = _make_item(1, tmp_path, micro_path=str(tmp_path / "missing-micro.png"), _skip_micro_write=True)
    report = ImageDatasetAuditor().audit(_manifest([item]), ImageAuditConfig())

    assert all(f.modality == ImageModality.MICRO for f in report.errors)
    assert report.checked_petri_images == 1
    assert report.checked_micro_images == 0
    assert report.failed_micro_images == 1
    assert report.failed_petri_images == 0


def test_does_not_modify_files(tmp_path):
    item = _make_item(1, tmp_path)
    petri_bytes_before = (tmp_path / "petri-1.jpg").read_bytes()
    micro_bytes_before = (tmp_path / "micro-1.png").read_bytes()

    ImageDatasetAuditor().audit(_manifest([item]), ImageAuditConfig())

    assert (tmp_path / "petri-1.jpg").read_bytes() == petri_bytes_before
    assert (tmp_path / "micro-1.png").read_bytes() == micro_bytes_before


def test_does_not_load_images_as_tensors(tmp_path):
    item = _make_item(1, tmp_path)
    ImageDatasetAuditor().audit(_manifest([item]), ImageAuditConfig())

    assert "torch" not in sys.modules
    assert "tensorflow" not in sys.modules


def test_result_is_deterministic(tmp_path):
    item1 = _make_item(1, tmp_path)
    item2 = _make_item(2, tmp_path)
    manifest = _manifest([item1, item2])
    config = ImageAuditConfig()

    report_a = ImageDatasetAuditor().audit(manifest, config)
    report_b = ImageDatasetAuditor().audit(manifest, config)

    assert report_a.status == report_b.status
    assert report_a.format_distribution == report_b.format_distribution
    assert report_a.color_mode_distribution == report_b.color_mode_distribution
    assert report_a.dimension_distribution == report_b.dimension_distribution
    assert report_a.file_size_distribution == report_b.file_size_distribution
    assert [f.code for f in report_a.errors] == [f.code for f in report_b.errors]
    assert [f.code for f in report_a.warnings] == [f.code for f in report_b.warnings]
