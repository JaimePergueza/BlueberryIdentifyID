from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_TERMS = ("bacteria", "fungi", "fungus", "colony", "species", "genus", "taxon", "diagnosis")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _resolve_dataset_path(dataset_dir: Path, root: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        base = root if root.is_absolute() else dataset_dir / root
        path = base / path
    return path.resolve()


def _images_from_path(path: Path) -> list[Path]:
    if path.is_file() and path.suffix.lower() == ".txt":
        return [Path(line.strip()).resolve() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
        return [path.resolve()]
    if path.is_dir():
        return sorted((p.resolve() for p in path.rglob("*") if p.suffix.lower() in IMAGE_EXTENSIONS), key=str)
    return []


def _label_path_for_image(image: Path) -> Path:
    parts = list(image.parts)
    if "images" in parts:
        index = len(parts) - 1 - parts[::-1].index("images")
        parts[index] = "labels"
        return Path(*parts).with_suffix(".txt")
    return image.with_suffix(".txt")


def validate_dataset(dataset_yaml: Path) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    split_summary: dict[str, dict[str, int]] = {}
    image_count = label_file_count = non_empty_label_file_count = annotation_count = 0
    dataset_yaml = dataset_yaml.resolve()

    if not dataset_yaml.is_file():
        return {
            "is_trainable": False,
            "dataset_yaml_path": str(dataset_yaml),
            "image_count": 0,
            "label_file_count": 0,
            "non_empty_label_file_count": 0,
            "annotation_count": 0,
            "split_summary": {},
            "issues": [{"code": "dataset_yaml_missing", "message": "dataset.yaml does not exist"}],
            "warnings": [],
        }

    data = yaml.safe_load(dataset_yaml.read_text(encoding="utf-8")) or {}
    root = Path(str(data.get("path", ".")))
    names = data.get("names")
    if "train" not in data:
        issues.append({"code": "train_missing", "message": "dataset.yaml must define train"})
    if "val" not in data:
        issues.append({"code": "val_missing", "message": "dataset.yaml must define val"})
    if not names:
        issues.append({"code": "names_missing", "message": "dataset.yaml must define names"})
    else:
        values = names.values() if isinstance(names, dict) else names
        for name in values:
            lowered = str(name).lower()
            if any(term in lowered for term in FORBIDDEN_TERMS):
                issues.append({"code": "forbidden_label_name", "message": f"forbidden non-generic label name: {name}"})

    for split in ("train", "val", "test"):
        if split not in data:
            continue
        split_path = _resolve_dataset_path(dataset_yaml.parent, root, str(data[split]))
        if not split_path.exists():
            issues.append({"code": "split_path_missing", "message": f"{split} path does not exist: {split_path}"})
        if _is_inside(split_path, REPO_ROOT):
            issues.append({"code": "split_path_inside_repo", "message": f"{split} path is inside repository: {split_path}"})
        images = _images_from_path(split_path)
        split_labels = split_non_empty = split_annotations = 0
        for image in images:
            image_count += 1
            if not image.exists():
                issues.append({"code": "image_missing", "message": f"image does not exist: {image}"})
                continue
            if _is_inside(image, REPO_ROOT):
                issues.append({"code": "image_inside_repo", "message": f"image is inside repository: {image}"})
            label = _label_path_for_image(image)
            if not label.is_file():
                issues.append({"code": "label_missing", "message": f"label missing for image {image}: {label}"})
                continue
            label_file_count += 1
            split_labels += 1
            lines = [line.strip() for line in label.read_text(encoding="utf-8").splitlines() if line.strip()]
            if lines:
                non_empty_label_file_count += 1
                split_non_empty += 1
            else:
                issues.append({"code": "label_empty", "message": f"label file is empty: {label}"})
            for line_number, line in enumerate(lines, start=1):
                parts = line.split()
                if len(parts) != 5:
                    issues.append({"code": "label_column_count", "message": f"{label}:{line_number} must have 5 columns"})
                    continue
                try:
                    class_id = int(parts[0])
                    values = [float(value) for value in parts[1:]]
                except ValueError:
                    issues.append({"code": "label_parse_error", "message": f"{label}:{line_number} has non-numeric values"})
                    continue
                if class_id < 0:
                    issues.append({"code": "class_id_invalid", "message": f"{label}:{line_number} class_id must be >= 0"})
                x_center, y_center, width, height = values
                if not all(0 <= value <= 1 for value in values):
                    issues.append({"code": "bbox_out_of_range", "message": f"{label}:{line_number} bbox values must be in [0,1]"})
                if width <= 0 or height <= 0:
                    issues.append({"code": "bbox_non_positive", "message": f"{label}:{line_number} width/height must be > 0"})
                annotation_count += 1
                split_annotations += 1
        split_summary[split] = {
            "images": len(images),
            "label_files": split_labels,
            "non_empty_label_files": split_non_empty,
            "annotations": split_annotations,
        }

    if split_summary.get("train", {}).get("annotations", 0) == 0:
        issues.append({"code": "train_labels_missing", "message": "train split must contain at least one annotation"})
    if split_summary.get("val", {}).get("annotations", 0) == 0:
        issues.append({"code": "val_labels_missing", "message": "val split must contain at least one annotation"})

    return {
        "is_trainable": not issues,
        "dataset_yaml_path": str(dataset_yaml),
        "image_count": image_count,
        "label_file_count": label_file_count,
        "non_empty_label_file_count": non_empty_label_file_count,
        "annotation_count": annotation_count,
        "split_summary": split_summary,
        "issues": issues,
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an external YOLO training dataset view.")
    parser.add_argument("--dataset-yaml", required=True)
    parser.add_argument("--emit-json", action="store_true")
    args = parser.parse_args(argv)
    result = validate_dataset(Path(args.dataset_yaml))
    print(json.dumps(result, indent=2, sort_keys=True) if args.emit_json else result)
    return 0 if result["is_trainable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
