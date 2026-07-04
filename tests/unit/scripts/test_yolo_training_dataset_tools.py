from __future__ import annotations

import ast
import json
from pathlib import Path

import yaml

from scripts import build_yolo_training_view, validate_yolo_training_dataset


def _source_bundle(tmp_path: Path) -> Path:
    image = tmp_path / "external_storage" / "petri-a.png"
    image.parent.mkdir()
    image.write_bytes(b"fake-png")
    bundle = tmp_path / "bundle"
    annotations = bundle / "annotations"
    annotations.mkdir(parents=True)
    manifest = {
        "format": "blueberry_manifest",
        "category": {"id": 1, "name": "candidate_region"},
        "images": [{"image_id": str(image), "petri_image_path": str(image), "split": "test", "width": 100, "height": 100}],
        "annotations": [
            {
                "annotation_id": "ann-1",
                "image_id": str(image),
                "bbox": [10, 20, 30, 40],
                "label": "candidate_region",
                "split": "test",
            }
        ],
    }
    (annotations / "blueberry_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return bundle


def test_build_view_creates_trainable_external_yolo_structure(tmp_path):
    bundle = _source_bundle(tmp_path)
    output_root = tmp_path / "outside_artifacts"

    result = build_yolo_training_view.build_view(bundle, output_root, "smoke", "smoke", "hardlink", False)

    dataset_yaml = Path(result["dataset_yaml_path"])
    assert dataset_yaml.is_file()
    label = output_root / "yolo_training_views" / "smoke" / "labels" / "train" / "petri-a.txt"
    assert label.read_text(encoding="utf-8").strip() == "0 0.250000 0.400000 0.300000 0.400000"
    validation = validate_yolo_training_dataset.validate_dataset(dataset_yaml)
    assert validation["is_trainable"] is True
    assert validation["split_summary"]["train"]["annotations"] == 1
    assert validation["split_summary"]["val"]["annotations"] == 1


def test_validator_rejects_empty_label_file(tmp_path):
    root = tmp_path / "dataset"
    image_dir = root / "images" / "train"
    label_dir = root / "labels" / "train"
    image_dir.mkdir(parents=True)
    label_dir.mkdir(parents=True)
    (image_dir / "a.png").write_bytes(b"fake")
    (label_dir / "a.txt").write_text("", encoding="utf-8")
    dataset_yaml = root / "dataset.yaml"
    dataset_yaml.write_text(yaml.safe_dump({"path": str(root), "train": "images/train", "val": "images/train", "names": {0: "candidate_region"}}), encoding="utf-8")

    result = validate_yolo_training_dataset.validate_dataset(dataset_yaml)

    assert result["is_trainable"] is False
    assert any(issue["code"] == "label_empty" for issue in result["issues"])


def test_scripts_do_not_import_training_modules_or_subprocess():
    for module in (build_yolo_training_view, validate_yolo_training_dataset):
        source = Path(module.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            node.module if isinstance(node, ast.ImportFrom) else alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        assert "ultralytics" not in imports
        assert "torch" not in imports
        assert "subprocess" not in imports
