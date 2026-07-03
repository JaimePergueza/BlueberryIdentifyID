import json
from dataclasses import asdict, replace

import pytest

from blueberry_microid.ml.configs.training_config import TrainingConfig
from blueberry_microid.ml.contracts.training_manifest import TrainingManifest, TrainingManifestItem
from blueberry_microid.ml.data.json_manifest_dataset_loader import JsonManifestDatasetLoader
from blueberry_microid.ml.training.trainer import TrainerPort, TrainingNotImplementedError
from blueberry_microid.ml.validation.image_path_validator import ImagePathValidator
from blueberry_microid.ml.validation.manifest_validator import ManifestValidator
from scripts.validate_training_manifest import main as validate_manifest_main


def _item(index: int, split: str, label: str = "suspicious_growth", **overrides) -> TrainingManifestItem:
    data = {
        "split": split,
        "analysis_run_id": f"run-{index}",
        "sample_id": f"sample-{index}",
        "sample_code": f"S-{index}",
        "lot_code": f"lot-{index}",
        "origin": "farm-a",
        "petri_image_path": f"petri-{index}.jpg",
        "micro_image_path": f"micro-{index}.png",
        "ground_truth_label": label,
        "prediction_label": label,
        "source_review_decision": "confirmed",
        "final_review_id": f"review-{index}",
    }
    data.update(overrides)
    return TrainingManifestItem(**data)


def _manifest(items=None, split_strategy="by_sample") -> TrainingManifest:
    items = items or [
        _item(1, "train", "suspicious_growth"),
        _item(2, "validation", "no_evident_growth"),
        _item(3, "test", "probable_fungal_growth"),
    ]
    return TrainingManifest(
        dataset_release_id="release-1",
        dataset_snapshot_id="snapshot-1",
        name="release",
        version="0.1.0",
        split_strategy=split_strategy,
        random_seed=42,
        train_ratio=0.7,
        validation_ratio=0.15,
        test_ratio=0.15,
        item_count=len(items),
        train_count=sum(item.split == "train" for item in items),
        validation_count=sum(item.split == "validation" for item in items),
        test_count=sum(item.split == "test" for item in items),
        label_distribution={},
        split_distribution={},
        items=items,
    )


def _config(**overrides) -> TrainingConfig:
    data = {"experiment_name": "exp", "output_dir": "out"}
    data.update(overrides)
    return TrainingConfig(**data)


def _report(manifest: TrainingManifest, config: TrainingConfig | None = None):
    return ManifestValidator().validate(manifest, config or _config())


def test_valid_manifest_passes():
    assert _report(_manifest()).is_valid is True


def test_manifest_without_train_fails():
    report = _report(_manifest([_item(1, "validation"), _item(2, "test")]))
    assert any("train" in error for error in report.errors)


def test_manifest_without_validation_fails():
    report = _report(_manifest([_item(1, "train"), _item(2, "test")]))
    assert any("validation" in error for error in report.errors)


def test_manifest_without_test_fails():
    report = _report(_manifest([_item(1, "train"), _item(2, "validation")]))
    assert any("test" in error for error in report.errors)


def test_item_without_petri_image_path_fails():
    report = _report(_manifest([_item(1, "train", petri_image_path=""), _item(2, "validation"), _item(3, "test")]))
    assert any("petri_image_path" in error for error in report.errors)


def test_item_without_micro_image_path_fails():
    report = _report(_manifest([_item(1, "train", micro_image_path=""), _item(2, "validation"), _item(3, "test")]))
    assert any("micro_image_path" in error for error in report.errors)


def test_invalid_label_fails():
    report = _report(_manifest([_item(1, "train", "aspergillus"), _item(2, "validation"), _item(3, "test")]))
    assert any("invalid ground_truth_label" in error for error in report.errors)


def test_invalid_split_fails():
    report = _report(_manifest([_item(1, "holdout"), _item(2, "validation"), _item(3, "test")]))
    assert any("invalid split" in error for error in report.errors)


def test_duplicate_analysis_run_id_fails():
    report = _report(_manifest([_item(1, "train"), _item(2, "validation", analysis_run_id="run-1"), _item(3, "test")]))
    assert any("duplicate analysis_run_id" in error for error in report.errors)


def test_inconclusive_fails_when_not_allowed():
    report = _report(_manifest([_item(1, "train", "inconclusive"), _item(2, "validation"), _item(3, "test")]))
    assert any("allow_inconclusive is false" in error for error in report.errors)


def test_inconclusive_passes_when_allowed():
    report = _report(
        _manifest([_item(1, "train", "inconclusive"), _item(2, "validation"), _item(3, "test")]),
        _config(allow_inconclusive=True),
    )
    assert report.is_valid is True


def test_require_lot_aware_split_fails_with_by_sample():
    report = _report(_manifest(split_strategy="by_sample"), _config(require_lot_aware_split=True))
    assert any("require_lot_aware_split" in error for error in report.errors)


def test_require_lot_aware_split_passes_with_by_lot():
    report = _report(_manifest(split_strategy="by_lot"), _config(require_lot_aware_split=True))
    assert report.is_valid is True


def test_sample_id_in_two_splits_fails():
    items = [_item(1, "train", sample_id="sample-x"), _item(2, "validation", sample_id="sample-x"), _item(3, "test")]
    report = _report(_manifest(items))
    assert any("sample_id 'sample-x'" in error for error in report.errors)


def test_lot_code_in_two_splits_fails_for_by_lot():
    items = [_item(1, "train", lot_code="lot-x"), _item(2, "validation", lot_code="lot-x"), _item(3, "test")]
    report = _report(_manifest(items, split_strategy="by_lot"))
    assert any("lot_code 'lot-x'" in error for error in report.errors)


def test_origin_lot_in_two_splits_fails_for_by_origin_lot():
    items = [
        _item(1, "train", origin="farm-x", lot_code="lot-x"),
        _item(2, "validation", origin="farm-x", lot_code="lot-x"),
        _item(3, "test"),
    ]
    report = _report(_manifest(items, split_strategy="by_origin_lot"))
    assert any("origin+lot 'farm-x|lot-x'" in error for error in report.errors)


def test_min_items_per_split_fails_when_not_met():
    report = _report(_manifest(), _config(min_items_per_split=2))
    assert any("below min_items_per_split" in error for error in report.errors)


def test_min_items_per_class_fails_when_not_met():
    report = _report(_manifest(), _config(min_items_per_class=2))
    assert any("below min_items_per_class" in error for error in report.errors)


def test_image_path_validator_detects_missing_file(tmp_path):
    existing = tmp_path / "petri.jpg"
    existing.write_text("not opened", encoding="utf-8")
    manifest = _manifest([
        _item(1, "train", petri_image_path=str(existing), micro_image_path=str(tmp_path / "missing.png")),
        _item(2, "validation", petri_image_path=str(existing), micro_image_path=str(existing)),
        _item(3, "test", petri_image_path=str(existing), micro_image_path=str(existing)),
    ])

    report = ImagePathValidator().validate(manifest)

    assert report.is_valid is False
    assert any("micro_image_path does not exist" in error for error in report.errors)


def test_json_manifest_dataset_loader_loads_valid_json(tmp_path):
    path = tmp_path / "manifest.json"
    payload = {
        "dataset_release_id": "release-1",
        "dataset_snapshot_id": "snapshot-1",
        "name": "release",
        "version": "0.1.0",
        "split_strategy": "by_sample",
        "random_seed": 42,
        "ratios": {"train": 0.7, "validation": 0.15, "test": 0.15},
        "counts": {"total": 3, "train": 1, "validation": 1, "test": 1},
        "items": [asdict(item) for item in _manifest().items],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")

    loader = JsonManifestDatasetLoader()
    manifest = loader.load_manifest(path)

    assert manifest.dataset_release_id == "release-1"
    assert len(loader.iter_items("train")) == 1


def test_trainer_port_base_does_not_train():
    trainer = TrainerPort()

    with pytest.raises(TrainingNotImplementedError):
        trainer.train(_manifest(), _config())


def test_cli_returns_exit_code_for_valid_and_invalid_manifest(tmp_path, capsys):
    valid_path = tmp_path / "valid.json"
    invalid_path = tmp_path / "invalid.json"
    base = {
        "dataset_release_id": "release-1",
        "dataset_snapshot_id": "snapshot-1",
        "name": "release",
        "version": "0.1.0",
        "split_strategy": "by_sample",
        "random_seed": 42,
        "ratios": {"train": 0.7, "validation": 0.15, "test": 0.15},
        "counts": {"total": 3, "train": 1, "validation": 1, "test": 1},
        "items": [asdict(item) for item in _manifest().items],
    }
    valid_path.write_text(json.dumps(base), encoding="utf-8")
    invalid = dict(base)
    invalid["items"] = [asdict(replace(_manifest().items[0], split="train"))]
    invalid_path.write_text(json.dumps(invalid), encoding="utf-8")

    assert validate_manifest_main([str(valid_path)]) == 0
    assert validate_manifest_main([str(invalid_path)]) == 1
    assert '"is_valid": true' in capsys.readouterr().out
