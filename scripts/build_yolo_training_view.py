from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _link_or_copy(source: Path, destination: Path, mode: str) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    if mode == "hardlink":
        try:
            os.link(source, destination)
            return "hardlink"
        except OSError:
            shutil.copy2(source, destination)
            return "copy_fallback"
    if mode == "symlink":
        os.symlink(source, destination)
        return "symlink"
    shutil.copy2(source, destination)
    return "copy"


def _normalize_bbox(bbox: list[float], width: float, height: float) -> str:
    x, y, w, h = bbox
    return f"0 {(x + w / 2) / width:.6f} {(y + h / 2) / height:.6f} {w / width:.6f} {h / height:.6f}"


def build_view(source_bundle_dir: Path, output_root_dir: Path, view_name: str, mode: str, link_mode: str, force: bool) -> dict[str, Any]:
    source_bundle_dir = source_bundle_dir.resolve()
    output_root_dir = output_root_dir.resolve()
    if _is_inside(output_root_dir, REPO_ROOT):
        raise ValueError(f"output_root_dir must be outside the repository: {output_root_dir}")
    manifest_path = source_bundle_dir / "annotations" / "blueberry_manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"blueberry manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    images_by_id = {image["image_id"]: image for image in manifest.get("images", [])}
    annotations = manifest.get("annotations", [])
    if not annotations:
        raise ValueError("source bundle has no annotations")
    view_dir = output_root_dir / "yolo_training_views" / view_name
    if view_dir.exists() and any(view_dir.iterdir()) and not force:
        raise ValueError(f"view directory already exists and is not empty: {view_dir}")
    if force and view_dir.exists():
        shutil.rmtree(view_dir)
    view_dir.mkdir(parents=True, exist_ok=True)

    split_names = ("train", "val", "test") if mode == "smoke" else ("train", "val")
    split_summary = {split: {"images": 0, "labels": 0, "annotations": 0} for split in split_names}
    link_results: list[dict[str, str]] = []
    annotation_count = 0
    used_sources: set[str] = set()

    for split in split_names:
        for annotation in annotations:
            image = images_by_id.get(annotation["image_id"])
            if not image:
                raise ValueError(f"annotation references missing image: {annotation['image_id']}")
            source_image = Path(image["petri_image_path"]).resolve()
            if not source_image.is_file():
                raise ValueError(f"source image not found: {source_image}")
            if _is_inside(source_image, REPO_ROOT):
                raise ValueError(f"source image must be outside repository: {source_image}")
            width = image.get("width")
            height = image.get("height")
            if not width or not height:
                raise ValueError(f"image dimensions missing for {source_image}")
            if annotation.get("label") != "candidate_region":
                raise ValueError(f"unsupported label: {annotation.get('label')}")
            destination_image = view_dir / "images" / split / source_image.name
            actual_link_mode = _link_or_copy(source_image, destination_image, link_mode)
            destination_label = view_dir / "labels" / split / f"{source_image.stem}.txt"
            destination_label.parent.mkdir(parents=True, exist_ok=True)
            destination_label.write_text(_normalize_bbox(annotation["bbox"], float(width), float(height)) + "\n", encoding="utf-8")
            used_sources.add(str(source_image))
            annotation_count += 1
            split_summary[split]["images"] += 1
            split_summary[split]["labels"] += 1
            split_summary[split]["annotations"] += 1
            link_results.append({"source": str(source_image), "destination": str(destination_image), "mode": actual_link_mode})

    dataset = {
        "path": str(view_dir),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {0: "candidate_region"},
    }
    dataset_yaml = view_dir / "dataset.yaml"
    dataset_yaml.write_text(yaml.safe_dump(dataset, sort_keys=False), encoding="utf-8")
    readme = view_dir / "README.md"
    readme.write_text(
        "# BlueberryMicroID YOLO Smoke Training View\n\n"
        "External technical view for local smoke training only. Images are linked or copied outside the repository.\n"
        "Single-fixture duplication across splits is permitted only in smoke mode and is not scientific validation.\n",
        encoding="utf-8",
    )
    payload = {
        "yolo_view_dir": str(view_dir),
        "dataset_yaml_path": str(dataset_yaml),
        "image_count": sum(split["images"] for split in split_summary.values()),
        "label_count": sum(split["labels"] for split in split_summary.values()),
        "annotation_count": annotation_count,
        "split_summary": split_summary,
        "link_results": link_results,
        "source_image_count": len(used_sources),
        "mode": mode,
        "contains_taxonomy": False,
        "scientific_claim": "none",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (view_dir / "manifest.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build an external YOLO images/labels training view from a bundle.")
    parser.add_argument("--source-bundle-dir", required=True)
    parser.add_argument("--output-root-dir", required=True)
    parser.add_argument("--view-name", required=True)
    parser.add_argument("--mode", choices=["smoke"], default="smoke")
    parser.add_argument("--link-mode", choices=["hardlink", "symlink", "copy"], default="hardlink")
    parser.add_argument("--emit-json", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = build_view(
            Path(args.source_bundle_dir), Path(args.output_root_dir), args.view_name, args.mode, args.link_mode, args.force
        )
    except Exception as exc:
        print(f"build_yolo_training_view failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True) if args.emit_json else result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
