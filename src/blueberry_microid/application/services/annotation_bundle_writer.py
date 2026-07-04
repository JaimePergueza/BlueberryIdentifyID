from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from blueberry_microid.application.services.annotation_bundle_validator import AnnotationBundleValidationReport
from blueberry_microid.domain.entities.annotation_bundle_file import AnnotationBundleFile
from blueberry_microid.domain.entities.petri_annotation_export_item import PetriAnnotationExportItem
from blueberry_microid.domain.entities.petri_annotation_export_run import PetriAnnotationExportRun
from blueberry_microid.domain.enums.annotation_bundle_file_role import AnnotationBundleFileRole
from blueberry_microid.ml.configs.annotation_bundle_config import AnnotationBundleConfig


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class AnnotationBundleWriteResult:
    files: list[AnnotationBundleFile]
    bundle_manifest: dict[str, Any]
    planned_files: list[dict[str, Any]] = field(default_factory=list)


class AnnotationBundleWriter:
    """Plan or write a filesystem bundle from a persisted Petri annotation export."""

    def write(
        self,
        *,
        bundle_run_id,
        export_run: PetriAnnotationExportRun,
        items: list[PetriAnnotationExportItem],
        config: AnnotationBundleConfig,
        validation_report: AnnotationBundleValidationReport,
    ) -> AnnotationBundleWriteResult:
        if config.copy_images:
            raise ValueError("not_supported_yet: copy_images=true is intentionally disabled in this phase")

        root = self._root(export_run, config)
        planned = self._planned_files(root, export_run, items, config)
        if config.dry_run:
            files = [
                AnnotationBundleFile(
                    bundle_run_id=bundle_run_id,
                    file_role=entry["role"],
                    file_path=str(root / entry["relative_path"]),
                    relative_path=entry["relative_path"],
                    content_type=entry["content_type"],
                )
                for entry in planned
            ]
            manifest = self._bundle_manifest(export_run, items, config, validation_report, files, dry_run=True)
            return AnnotationBundleWriteResult(files=files, bundle_manifest=manifest, planned_files=planned)

        if root.exists() and any(root.iterdir()) and not config.overwrite_existing:
            raise ValueError(f"output_dir already exists and is not empty: {root}")
        root.mkdir(parents=True, exist_ok=True)

        files: list[AnnotationBundleFile] = []
        for entry in planned:
            if entry["role"] == AnnotationBundleFileRole.BUNDLE_MANIFEST:
                continue
            relative = entry["relative_path"]
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            content = self._content_for(entry, export_run, items, config, validation_report, files)
            path.write_text(content, encoding="utf-8")
            files.append(
                AnnotationBundleFile(
                    bundle_run_id=bundle_run_id,
                    file_role=entry["role"],
                    file_path=str(path),
                    relative_path=relative,
                    content_type=entry["content_type"],
                    size_bytes=path.stat().st_size,
                    checksum_sha256=self._sha256(path),
                )
            )

        manifest_path = root / "manifest.json"
        manifest = self._bundle_manifest(export_run, items, config, validation_report, files, dry_run=False)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        files.append(
            AnnotationBundleFile(
                bundle_run_id=bundle_run_id,
                file_role=AnnotationBundleFileRole.BUNDLE_MANIFEST,
                file_path=str(manifest_path),
                relative_path="manifest.json",
                content_type="application/json",
                size_bytes=manifest_path.stat().st_size,
                checksum_sha256=self._sha256(manifest_path),
            )
        )
        manifest = self._bundle_manifest(export_run, items, config, validation_report, files, dry_run=False)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        files[-1] = AnnotationBundleFile(
            bundle_run_id=bundle_run_id,
            file_role=AnnotationBundleFileRole.BUNDLE_MANIFEST,
            file_path=str(manifest_path),
            relative_path="manifest.json",
            content_type="application/json",
            size_bytes=manifest_path.stat().st_size,
            checksum_sha256=self._sha256(manifest_path),
        )
        return AnnotationBundleWriteResult(files=files, bundle_manifest=manifest, planned_files=planned)

    @staticmethod
    def _root(export_run: PetriAnnotationExportRun, config: AnnotationBundleConfig) -> Path:
        base = Path(config.output_dir) if config.output_dir else Path("annotation_bundle")
        if config.bundle_name:
            return base / config.bundle_name
        return base

    def _planned_files(
        self,
        root: Path,
        export_run: PetriAnnotationExportRun,
        items: list[PetriAnnotationExportItem],
        config: AnnotationBundleConfig,
    ) -> list[dict[str, Any]]:
        planned: list[dict[str, Any]] = []
        if config.include_readme:
            planned.append({"role": AnnotationBundleFileRole.README, "relative_path": "README.md", "content_type": "text/markdown"})
        if config.include_blueberry_manifest:
            planned.append(
                {
                    "role": AnnotationBundleFileRole.BLUEBERRY_MANIFEST,
                    "relative_path": "annotations/blueberry_manifest.json",
                    "content_type": "application/json",
                }
            )
        if config.include_coco:
            planned.append(
                {
                    "role": AnnotationBundleFileRole.COCO_ANNOTATIONS,
                    "relative_path": "annotations/coco_annotations.json",
                    "content_type": "application/json",
                }
            )
        if config.include_yolo:
            for image_path, split in self._image_splits(items).items():
                label_name = Path(image_path).with_suffix(".txt").name
                relative = f"annotations/yolo/{split}/{label_name}" if config.preserve_split_dirs else f"annotations/yolo/{label_name}"
                planned.append(
                    {
                        "role": AnnotationBundleFileRole.YOLO_LABEL,
                        "relative_path": relative,
                        "content_type": "text/plain",
                        "image_path": image_path,
                    }
                )
        if config.include_dataset_yaml:
            planned.append({"role": AnnotationBundleFileRole.DATASET_YAML, "relative_path": "dataset.yaml", "content_type": "text/yaml"})
        planned.append({"role": AnnotationBundleFileRole.BUNDLE_MANIFEST, "relative_path": "manifest.json", "content_type": "application/json"})
        return sorted(planned, key=lambda item: item["relative_path"])

    def _content_for(
        self,
        entry: dict[str, Any],
        export_run: PetriAnnotationExportRun,
        items: list[PetriAnnotationExportItem],
        config: AnnotationBundleConfig,
        validation_report: AnnotationBundleValidationReport,
        files: list[AnnotationBundleFile],
    ) -> str:
        role = entry["role"]
        if role == AnnotationBundleFileRole.README:
            return self._readme(export_run, config, validation_report)
        if role == AnnotationBundleFileRole.BLUEBERRY_MANIFEST:
            return json.dumps(self._blueberry_manifest(export_run, items), indent=2, sort_keys=True)
        if role == AnnotationBundleFileRole.COCO_ANNOTATIONS:
            return json.dumps(self._coco_manifest(export_run, items), indent=2, sort_keys=True)
        if role == AnnotationBundleFileRole.YOLO_LABEL:
            return "\n".join(self._yolo_lines(export_run, items, entry["image_path"])) + "\n"
        if role == AnnotationBundleFileRole.DATASET_YAML:
            return self._dataset_yaml(items, config)
        return json.dumps(self._bundle_manifest(export_run, items, config, validation_report, files, dry_run=False), indent=2, sort_keys=True)

    @staticmethod
    def _blueberry_manifest(export_run: PetriAnnotationExportRun, items: list[PetriAnnotationExportItem]) -> dict:
        manifest = export_run.output_manifest or {}
        if manifest.get("format") == "blueberry_manifest":
            return manifest
        return {
            "format": "blueberry_manifest",
            "dataset_release_id": str(export_run.dataset_release_id),
            "petri_segmentation_run_id": str(export_run.petri_segmentation_run_id),
            "category": {"id": 1, "name": "candidate_region"},
            "images": [{"image_id": path, "petri_image_path": path, "split": split} for path, split in AnnotationBundleWriter._image_splits(items).items()],
            "annotations": [
                {
                    "annotation_id": str(item.id),
                    "image_id": item.petri_image_path,
                    "petri_region_review_id": str(item.petri_region_review_id),
                    "petri_segmentation_region_id": str(item.petri_segmentation_region_id),
                    "bbox": [item.bbox_x, item.bbox_y, item.bbox_width, item.bbox_height],
                    "bbox_source": item.bbox_source.value,
                    "decision": item.export_payload.get("decision", "candidate_valid"),
                    "split": item.split.value,
                    "label": item.export_label,
                }
                for item in items
            ],
        }

    @staticmethod
    def _coco_manifest(export_run: PetriAnnotationExportRun, items: list[PetriAnnotationExportItem]) -> dict:
        manifest = export_run.output_manifest or {}
        if {"images", "annotations", "categories"}.issubset(manifest):
            return manifest
        return {
            "info": {
                "description": "BlueberryMicroID reviewed Petri candidate-region annotations",
                "dataset_release_id": str(export_run.dataset_release_id),
                "petri_segmentation_run_id": str(export_run.petri_segmentation_run_id),
            },
            "images": [
                {"id": path, "file_name": path, "split": split}
                for path, split in AnnotationBundleWriter._image_splits(items).items()
            ],
            "annotations": [
                {
                    "id": str(item.id),
                    "image_id": item.petri_image_path,
                    "category_id": 1,
                    "bbox": [item.bbox_x, item.bbox_y, item.bbox_width, item.bbox_height],
                    "area": item.bbox_width * item.bbox_height,
                    "iscrowd": 0,
                }
                for item in items
            ],
            "categories": [{"id": 1, "name": "candidate_region"}],
        }

    @staticmethod
    def _yolo_lines(export_run: PetriAnnotationExportRun, items: list[PetriAnnotationExportItem], image_path: str) -> list[str]:
        manifest = export_run.output_manifest or {}
        for label in manifest.get("labels", []):
            if label.get("image_path") == image_path:
                return sorted(label.get("lines", []))
        lines: list[str] = []
        for item in items:
            if item.petri_image_path != image_path:
                continue
            image_payload = next(
                (
                    image
                    for image in manifest.get("images", [])
                    if image.get("petri_image_path") == image_path or image.get("image_id") == image_path
                ),
                {},
            )
            width = image_payload.get("width")
            height = image_payload.get("height")
            if not width or not height:
                continue
            x_center = (item.bbox_x + item.bbox_width / 2) / width
            y_center = (item.bbox_y + item.bbox_height / 2) / height
            bbox_width = item.bbox_width / width
            bbox_height = item.bbox_height / height
            lines.append(f"0 {x_center:.6f} {y_center:.6f} {bbox_width:.6f} {bbox_height:.6f}")
        if lines:
            return sorted(lines)
        return []

    @staticmethod
    def _image_splits(items: list[PetriAnnotationExportItem]) -> dict[str, str]:
        return {item.petri_image_path: item.split.value for item in sorted(items, key=lambda item: item.petri_image_path)}

    @staticmethod
    def _dataset_yaml(items: list[PetriAnnotationExportItem], config: AnnotationBundleConfig) -> str:
        splits = sorted(set(item.split.value for item in items))
        lines = [
            "# BlueberryMicroID annotation bundle; YOLO here means label format only.",
            "path: .",
            "copy_images: false",
            "external_images: true",
            "names:",
            "  0: candidate_region",
        ]
        for split in splits:
            target = f"images/{split}" if config.copy_images else "external_image_paths"
            lines.append(f"{split}: {target}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _readme(
        export_run: PetriAnnotationExportRun,
        config: AnnotationBundleConfig,
        validation_report: AnnotationBundleValidationReport,
    ) -> str:
        return (
            "# BlueberryMicroID Petri Annotation Bundle\n\n"
            "This bundle contains supervised annotation files derived from final human-reviewed Petri candidate regions.\n\n"
            "- YOLO means label text format only, not a model.\n"
            "- COCO means annotation JSON only.\n"
            "- Images are not copied by default and original images are not modified.\n"
            "- Category is generic: candidate_region.\n"
            "- No taxonomy, diagnosis, model weights, or training artifacts are included.\n\n"
            f"Source export run: {export_run.id}\n\n"
            f"Validation valid: {validation_report.is_valid}\n"
        )

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _bundle_manifest(
        export_run: PetriAnnotationExportRun,
        items: list[PetriAnnotationExportItem],
        config: AnnotationBundleConfig,
        validation_report: AnnotationBundleValidationReport,
        files: list[AnnotationBundleFile],
        *,
        dry_run: bool,
    ) -> dict[str, Any]:
        return {
            "generated_at": _iso_now(),
            "dry_run": dry_run,
            "source_petri_annotation_export_run_id": str(export_run.id),
            "dataset_release_id": str(export_run.dataset_release_id),
            "petri_segmentation_run_id": str(export_run.petri_segmentation_run_id),
            "annotation_count": len(items),
            "image_count": len({item.petri_image_path for item in items}),
            "copy_images": False,
            "contains_taxonomy": False,
            "contains_training": False,
            "files": [
                {
                    "role": file.file_role.value,
                    "relative_path": file.relative_path,
                    "size_bytes": file.size_bytes,
                    "checksum_sha256": file.checksum_sha256,
                }
                for file in sorted(files, key=lambda file: file.relative_path)
            ],
            "validation_summary": validation_report.to_dict(),
            "config": config.to_dict(),
        }
