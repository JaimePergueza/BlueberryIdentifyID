from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from typing import Any, Optional
from uuid import UUID

from blueberry_microid.domain.entities.annotation_bundle_file import AnnotationBundleFile
from blueberry_microid.domain.entities.annotation_bundle_run import AnnotationBundleRun
from blueberry_microid.domain.entities.annotation_quality_gate_issue import AnnotationQualityGateIssue
from blueberry_microid.domain.enums.annotation_bundle_file_role import AnnotationBundleFileRole
from blueberry_microid.domain.enums.annotation_bundle_status import AnnotationBundleStatus
from blueberry_microid.domain.enums.annotation_quality_gate_issue_severity import (
    AnnotationQualityGateIssueSeverity,
)
from blueberry_microid.domain.enums.annotation_quality_gate_status import AnnotationQualityGateStatus
from blueberry_microid.ml.configs.annotation_quality_gate_config import AnnotationQualityGateConfig


_FORBIDDEN_TERMS = ("bacteria", "fungi", "fungus", "colony", "species", "genus", "taxon", "diagnosis")


@dataclass(frozen=True)
class AnnotationQualityGateReport:
    is_passed: bool
    status: AnnotationQualityGateStatus
    issues: list[AnnotationQualityGateIssue]
    total_images: int
    total_annotations: int
    split_distribution: dict[str, dict[str, int]]
    bbox_statistics: dict[str, Any]
    category_distribution: dict[str, int]
    file_checks: dict[str, bool]
    recommendations: list[str] = field(default_factory=list)

    @property
    def errors(self) -> list[AnnotationQualityGateIssue]:
        return [issue for issue in self.issues if issue.severity == AnnotationQualityGateIssueSeverity.ERROR]

    @property
    def warnings(self) -> list[AnnotationQualityGateIssue]:
        return [issue for issue in self.issues if issue.severity == AnnotationQualityGateIssueSeverity.WARNING]

    def summary(self) -> dict[str, Any]:
        return {
            "is_passed": self.is_passed,
            "status": self.status.value,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "file_checks": self.file_checks,
            "recommendations": self.recommendations,
        }


class AnnotationQualityGateValidator:
    """Technical readiness checks for supervised annotation bundles.

    It inspects persisted bundle metadata and text manifests only. It never
    opens image bytes, never trains, and never treats YOLO labels as a model.
    """

    def validate(
        self,
        bundle_run: AnnotationBundleRun,
        bundle_files: list[AnnotationBundleFile],
        config: AnnotationQualityGateConfig,
    ) -> AnnotationQualityGateReport:
        issues: list[AnnotationQualityGateIssue] = []
        files_by_role = self._files_by_role(bundle_files)
        file_checks: dict[str, bool] = {}

        self._validate_bundle_state(bundle_run, config, issues)
        self._validate_expected_files(files_by_role, config, issues, file_checks)

        blueberry = self._read_json_role(files_by_role, AnnotationBundleFileRole.BLUEBERRY_MANIFEST, issues)
        coco = self._read_json_role(files_by_role, AnnotationBundleFileRole.COCO_ANNOTATIONS, issues)
        yolo_lines = self._read_yolo_lines(files_by_role, issues)
        self._read_dataset_yaml(files_by_role, issues)

        images, annotations, categories = self._extract_annotation_view(bundle_run, blueberry, coco)
        self._validate_categories(categories, config, issues)
        self._validate_splits(images, annotations, config, issues)
        self._validate_bboxes(annotations, images, config, issues)
        self._validate_support(images, annotations, categories, config, issues)
        if config.validate_coco and coco:
            self._validate_coco(coco, config, issues)
        if config.validate_yolo and yolo_lines:
            self._validate_yolo(yolo_lines, issues)

        split_distribution = self._split_distribution(images, annotations, config)
        bbox_statistics = self._bbox_statistics(annotations)
        category_distribution = self._category_distribution(categories, annotations)
        status = self._status(issues)
        recommendations = []
        if status != AnnotationQualityGateStatus.PASSED:
            recommendations.append("review quality gate issues before any future training workflow")
        if bundle_run.dry_run:
            recommendations.append("create a real annotation bundle before training")

        return AnnotationQualityGateReport(
            is_passed=status == AnnotationQualityGateStatus.PASSED,
            status=status,
            issues=issues,
            total_images=len(images),
            total_annotations=len(annotations),
            split_distribution=split_distribution,
            bbox_statistics=bbox_statistics,
            category_distribution=category_distribution,
            file_checks=file_checks,
            recommendations=recommendations,
        )

    def _validate_bundle_state(
        self,
        bundle_run: AnnotationBundleRun,
        config: AnnotationQualityGateConfig,
        issues: list[AnnotationQualityGateIssue],
    ) -> None:
        if bundle_run.status == AnnotationBundleStatus.FAILED:
            self._issue(issues, "error", "bundle_not_completed", "annotation bundle run failed")
        if config.require_completed_bundle and bundle_run.status != AnnotationBundleStatus.COMPLETED:
            self._issue(
                issues,
                "error",
                "bundle_not_completed",
                "annotation bundle must be completed before it can pass the quality gate",
            )
        elif bundle_run.status == AnnotationBundleStatus.DRY_RUN:
            self._issue(issues, "warning", "bundle_not_completed", "annotation bundle is dry-run only")

    def _validate_expected_files(
        self,
        files_by_role: dict[AnnotationBundleFileRole, list[AnnotationBundleFile]],
        config: AnnotationQualityGateConfig,
        issues: list[AnnotationQualityGateIssue],
        file_checks: dict[str, bool],
    ) -> None:
        expected = {
            AnnotationBundleFileRole.BUNDLE_MANIFEST: "manifest.json",
            AnnotationBundleFileRole.COCO_ANNOTATIONS: "coco_annotations.json",
            AnnotationBundleFileRole.YOLO_LABEL: "yolo label files",
            AnnotationBundleFileRole.BLUEBERRY_MANIFEST: "blueberry_manifest.json",
            AnnotationBundleFileRole.DATASET_YAML: "dataset.yaml",
        }
        enabled = {
            AnnotationBundleFileRole.BUNDLE_MANIFEST: True,
            AnnotationBundleFileRole.COCO_ANNOTATIONS: config.validate_coco,
            AnnotationBundleFileRole.YOLO_LABEL: config.validate_yolo,
            AnnotationBundleFileRole.BLUEBERRY_MANIFEST: config.validate_blueberry_manifest,
            AnnotationBundleFileRole.DATASET_YAML: config.validate_dataset_yaml,
        }
        code_by_role = {
            AnnotationBundleFileRole.BUNDLE_MANIFEST: "file_missing",
            AnnotationBundleFileRole.COCO_ANNOTATIONS: "coco_missing",
            AnnotationBundleFileRole.YOLO_LABEL: "yolo_missing",
            AnnotationBundleFileRole.BLUEBERRY_MANIFEST: "blueberry_manifest_missing",
            AnnotationBundleFileRole.DATASET_YAML: "dataset_yaml_missing",
        }
        for role, label in expected.items():
            if not enabled[role]:
                continue
            files = files_by_role.get(role, [])
            file_checks[role.value] = bool(files)
            if not files:
                self._issue(issues, "error", code_by_role[role], f"expected bundle file missing: {label}")
                continue
            if config.validate_files_exist:
                existing = [Path(file.file_path).exists() for file in files]
                file_checks[f"{role.value}_exists"] = all(existing)
                for file, exists in zip(files, existing):
                    if not exists:
                        self._issue(
                            issues,
                            "error",
                            "file_missing",
                            f"bundle file does not exist: {file.relative_path}",
                            details={"relative_path": file.relative_path},
                        )

    def _extract_annotation_view(
        self,
        bundle_run: AnnotationBundleRun,
        blueberry: Optional[dict],
        coco: Optional[dict],
    ) -> tuple[dict[str, dict], list[dict], dict[int, str]]:
        if blueberry:
            images = {}
            for image in blueberry.get("images", []):
                image_id = str(image.get("image_id") or image.get("petri_image_path"))
                images[image_id] = {
                    "id": image_id,
                    "path": image.get("petri_image_path") or image_id,
                    "split": image.get("split") or "train",
                    "width": image.get("width"),
                    "height": image.get("height"),
                }
            annotations = []
            for annotation in blueberry.get("annotations", []):
                image_id = str(annotation.get("image_id") or annotation.get("petri_image_path"))
                annotations.append(
                    {
                        "id": str(annotation.get("annotation_id") or annotation.get("id") or len(annotations)),
                        "image_id": image_id,
                        "bbox": annotation.get("bbox"),
                        "split": annotation.get("split") or images.get(image_id, {}).get("split") or "train",
                        "category": annotation.get("label", "candidate_region"),
                    }
                )
                images.setdefault(
                    image_id,
                    {"id": image_id, "path": image_id, "split": annotation.get("split") or "train", "width": None, "height": None},
                )
            categories = {1: (blueberry.get("category") or {}).get("name", "candidate_region")}
            return images, annotations, categories

        if coco:
            images = {
                str(image.get("id")): {
                    "id": str(image.get("id")),
                    "path": image.get("file_name") or str(image.get("id")),
                    "split": image.get("split"),
                    "width": image.get("width"),
                    "height": image.get("height"),
                }
                for image in coco.get("images", [])
            }
            categories = {category.get("id"): category.get("name") for category in coco.get("categories", [])}
            annotations = [
                {
                    "id": str(annotation.get("id")),
                    "image_id": str(annotation.get("image_id")),
                    "bbox": annotation.get("bbox"),
                    "split": images.get(str(annotation.get("image_id")), {}).get("split"),
                    "category": categories.get(annotation.get("category_id"), "candidate_region"),
                }
                for annotation in coco.get("annotations", [])
            ]
            return images, annotations, categories

        return {}, [], {1: "candidate_region"}

    def _validate_categories(
        self,
        categories: dict[Any, str],
        config: AnnotationQualityGateConfig,
        issues: list[AnnotationQualityGateIssue],
    ) -> None:
        for category in categories.values():
            lowered = str(category).lower()
            if any(term in lowered for term in _FORBIDDEN_TERMS):
                self._issue(issues, "error", "taxonomic_category_detected", f"taxonomic category detected: {category}")
            if category not in config.allowed_categories:
                self._issue(issues, "error", "category_not_allowed", f"category not allowed: {category}")

    def _validate_splits(
        self,
        images: dict[str, dict],
        annotations: list[dict],
        config: AnnotationQualityGateConfig,
        issues: list[AnnotationQualityGateIssue],
    ) -> None:
        for image in images.values():
            split = image.get("split")
            if split is not None and split not in config.allowed_splits:
                self._issue(issues, "error", "invalid_split", f"invalid split for image: {split}", split=None)
        for annotation in annotations:
            split = annotation.get("split")
            if split is not None and split not in config.allowed_splits:
                self._issue(issues, "error", "invalid_split", f"invalid split for annotation: {split}", split=None)

    def _validate_bboxes(
        self,
        annotations: list[dict],
        images: dict[str, dict],
        config: AnnotationQualityGateConfig,
        issues: list[AnnotationQualityGateIssue],
    ) -> None:
        seen: set[tuple] = set()
        for annotation in annotations:
            bbox = annotation.get("bbox")
            ref = annotation.get("id")
            image_id = annotation.get("image_id")
            if not (isinstance(bbox, list) and len(bbox) == 4):
                self._issue(issues, "error", "bbox_invalid", "bbox must be [x, y, width, height]", annotation_ref=ref)
                continue
            x, y, width, height = bbox
            if width <= 0:
                self._issue(issues, "error", "bbox_invalid", "bbox width must be positive", annotation_ref=ref)
            if height <= 0:
                self._issue(issues, "error", "bbox_invalid", "bbox height must be positive", annotation_ref=ref)
            if x < 0 or y < 0:
                self._issue(issues, "error", "bbox_invalid", "bbox x/y must be non-negative", annotation_ref=ref)
            if 0 < width < config.min_bbox_width_px or 0 < height < config.min_bbox_height_px:
                self._issue(issues, "warning", "bbox_too_small", "bbox is smaller than configured minimum", annotation_ref=ref)
            image = images.get(str(image_id), {})
            img_width = image.get("width")
            img_height = image.get("height")
            if img_width and img_height and (x + width > img_width or y + height > img_height):
                self._issue(issues, "error", "bbox_out_of_bounds", "bbox exceeds image dimensions", annotation_ref=ref)
            if img_width and img_height and img_width > 0 and img_height > 0:
                ratio = (width * height) / (img_width * img_height)
                if config.max_bbox_area_ratio is not None and ratio > config.max_bbox_area_ratio:
                    self._issue(issues, "warning", "bbox_area_outlier", "bbox area ratio is above configured maximum", annotation_ref=ref)
                if config.min_bbox_area_ratio is not None and ratio < config.min_bbox_area_ratio:
                    self._issue(issues, "warning", "bbox_area_outlier", "bbox area ratio is below configured minimum", annotation_ref=ref)
            key = (image_id, tuple(bbox), annotation.get("category"))
            if key in seen:
                severity = "error" if config.fail_on_duplicate_bboxes else "warning"
                if config.fail_on_duplicate_bboxes or config.warn_on_duplicate_bboxes:
                    self._issue(issues, severity, "duplicate_bbox", "duplicate bbox detected", annotation_ref=ref)
            seen.add(key)

    def _validate_support(
        self,
        images: dict[str, dict],
        annotations: list[dict],
        categories: dict[Any, str],
        config: AnnotationQualityGateConfig,
        issues: list[AnnotationQualityGateIssue],
    ) -> None:
        if len(images) < config.min_total_images:
            self._issue(issues, "error", "insufficient_images", "total image count below configured minimum")
        if len(annotations) < config.min_total_annotations:
            self._issue(issues, "error", "insufficient_annotations", "total annotation count below configured minimum")
        by_split = self._split_distribution(images, annotations, config)
        for split in config.allowed_splits:
            image_count = by_split.get(split, {}).get("images", 0)
            annotation_count = by_split.get(split, {}).get("annotations", 0)
            if config.fail_on_empty_split and (image_count == 0 or annotation_count == 0):
                self._issue(issues, "error", "empty_split", f"split has no images or annotations: {split}", split=split)
            if image_count < config.min_images_per_split:
                self._issue(issues, "error", "insufficient_images", "split image count below minimum", split=split)
            if annotation_count < config.min_annotations_per_split:
                self._issue(issues, "error", "insufficient_annotations", "split annotation count below minimum", split=split)
        annotated_images = {str(annotation.get("image_id")) for annotation in annotations}
        for image_id, image in images.items():
            if image_id not in annotated_images:
                severity = "error" if config.fail_on_images_without_annotations else "warning"
                if config.fail_on_images_without_annotations or config.warn_on_images_without_annotations:
                    self._issue(
                        issues,
                        severity,
                        "image_without_annotations",
                        "image has no annotations",
                        split=image.get("split"),
                        image_path=image.get("path"),
                    )
        if len(set(categories.values())) <= 1:
            severity = "error" if config.fail_on_single_class else "warning"
            if config.fail_on_single_class or config.warn_on_single_class:
                self._issue(issues, severity, "single_class_only", "bundle contains a single category only")

    def _validate_coco(
        self,
        coco: dict,
        config: AnnotationQualityGateConfig,
        issues: list[AnnotationQualityGateIssue],
    ) -> None:
        image_ids = {image.get("id") for image in coco.get("images", [])}
        category_ids = {category.get("id") for category in coco.get("categories", [])}
        annotation_ids: set[Any] = set()
        for annotation in coco.get("annotations", []):
            if annotation.get("id") in annotation_ids:
                self._issue(issues, "error", "manifest_inconsistent", "COCO annotation ids must be unique")
            annotation_ids.add(annotation.get("id"))
            if annotation.get("image_id") not in image_ids:
                self._issue(issues, "error", "manifest_inconsistent", "COCO annotation image_id does not exist")
            if annotation.get("category_id") not in category_ids:
                self._issue(issues, "error", "category_not_allowed", "COCO category_id is not declared")
            bbox = annotation.get("bbox")
            if not (isinstance(bbox, list) and len(bbox) == 4):
                self._issue(issues, "error", "bbox_invalid", "COCO bbox must be [x, y, width, height]")
                continue
            if bbox[2] <= 0 or bbox[3] <= 0:
                self._issue(issues, "error", "bbox_invalid", "COCO bbox width/height must be positive")
            if annotation.get("area", 0) <= 0:
                self._issue(issues, "error", "bbox_invalid", "COCO area must be positive")

    def _validate_yolo(self, yolo_lines: list[tuple[str, str]], issues: list[AnnotationQualityGateIssue]) -> None:
        for relative_path, line in yolo_lines:
            parts = line.split()
            if len(parts) != 5:
                self._issue(issues, "error", "manifest_inconsistent", "YOLO label line must have 5 fields", details={"file": relative_path})
                continue
            try:
                class_id = int(parts[0])
                coords = [float(value) for value in parts[1:]]
            except ValueError:
                self._issue(issues, "error", "manifest_inconsistent", "YOLO label line fields must be numeric", details={"file": relative_path})
                continue
            if class_id < 0:
                self._issue(issues, "error", "category_not_allowed", "YOLO class id must be non-negative", details={"file": relative_path})
            if not all(0.0 <= value <= 1.0 for value in coords):
                self._issue(issues, "error", "bbox_invalid", "YOLO coordinates must be normalized between 0 and 1", details={"file": relative_path})
            if coords[2] <= 0 or coords[3] <= 0:
                self._issue(issues, "error", "bbox_invalid", "YOLO normalized width/height must be positive", details={"file": relative_path})

    @staticmethod
    def _split_distribution(
        images: dict[str, dict],
        annotations: list[dict],
        config: AnnotationQualityGateConfig,
    ) -> dict[str, dict[str, int]]:
        distribution = {split: {"images": 0, "annotations": 0} for split in config.allowed_splits}
        for image in images.values():
            split = image.get("split")
            if split in distribution:
                distribution[split]["images"] += 1
        for annotation in annotations:
            split = annotation.get("split")
            if split in distribution:
                distribution[split]["annotations"] += 1
        return distribution

    @staticmethod
    def _bbox_statistics(annotations: list[dict]) -> dict[str, Any]:
        widths = []
        heights = []
        areas = []
        for annotation in annotations:
            bbox = annotation.get("bbox")
            if isinstance(bbox, list) and len(bbox) == 4 and bbox[2] > 0 and bbox[3] > 0:
                widths.append(bbox[2])
                heights.append(bbox[3])
                areas.append(bbox[2] * bbox[3])
        if not widths:
            return {"count": 0}
        return {
            "count": len(widths),
            "min_width": min(widths),
            "max_width": max(widths),
            "mean_width": mean(widths),
            "min_height": min(heights),
            "max_height": max(heights),
            "mean_height": mean(heights),
            "min_area": min(areas),
            "max_area": max(areas),
            "mean_area": mean(areas),
        }

    @staticmethod
    def _category_distribution(categories: dict[Any, str], annotations: list[dict]) -> dict[str, int]:
        distribution = {str(category): 0 for category in categories.values()}
        for annotation in annotations:
            category = str(annotation.get("category", "candidate_region"))
            distribution[category] = distribution.get(category, 0) + 1
        return distribution

    @staticmethod
    def _status(issues: list[AnnotationQualityGateIssue]) -> AnnotationQualityGateStatus:
        if any(issue.severity == AnnotationQualityGateIssueSeverity.ERROR for issue in issues):
            return AnnotationQualityGateStatus.FAILED
        if issues:
            return AnnotationQualityGateStatus.WARNING
        return AnnotationQualityGateStatus.PASSED

    @staticmethod
    def _files_by_role(bundle_files: list[AnnotationBundleFile]) -> dict[AnnotationBundleFileRole, list[AnnotationBundleFile]]:
        grouped: dict[AnnotationBundleFileRole, list[AnnotationBundleFile]] = {}
        for file in bundle_files:
            grouped.setdefault(file.file_role, []).append(file)
        return grouped

    def _read_json_role(
        self,
        files_by_role: dict[AnnotationBundleFileRole, list[AnnotationBundleFile]],
        role: AnnotationBundleFileRole,
        issues: list[AnnotationQualityGateIssue],
    ) -> Optional[dict]:
        files = files_by_role.get(role, [])
        if not files:
            return None
        path = Path(files[0].file_path)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self._issue(issues, "error", "manifest_inconsistent", f"cannot read JSON bundle file: {files[0].relative_path}", details={"error": str(exc)})
            return None

    def _read_yolo_lines(
        self,
        files_by_role: dict[AnnotationBundleFileRole, list[AnnotationBundleFile]],
        issues: list[AnnotationQualityGateIssue],
    ) -> list[tuple[str, str]]:
        lines: list[tuple[str, str]] = []
        for file in files_by_role.get(AnnotationBundleFileRole.YOLO_LABEL, []):
            path = Path(file.file_path)
            if not path.exists():
                continue
            try:
                for line in path.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        lines.append((file.relative_path, line.strip()))
            except OSError as exc:
                self._issue(issues, "error", "manifest_inconsistent", f"cannot read YOLO label file: {file.relative_path}", details={"error": str(exc)})
        return lines

    def _read_dataset_yaml(
        self,
        files_by_role: dict[AnnotationBundleFileRole, list[AnnotationBundleFile]],
        issues: list[AnnotationQualityGateIssue],
    ) -> None:
        files = files_by_role.get(AnnotationBundleFileRole.DATASET_YAML, [])
        if not files:
            return
        path = Path(files[0].file_path)
        if not path.exists():
            return
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            self._issue(issues, "error", "manifest_inconsistent", "cannot read dataset.yaml", details={"error": str(exc)})
            return
        if "names:" not in content or "candidate_region" not in content:
            self._issue(issues, "error", "dataset_yaml_missing", "dataset.yaml does not declare candidate_region")

    @staticmethod
    def _issue(
        issues: list[AnnotationQualityGateIssue],
        severity: str,
        code: str,
        message: str,
        *,
        split: Optional[str] = None,
        image_path: Optional[str] = None,
        annotation_ref: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> None:
        issues.append(
            AnnotationQualityGateIssue(
                quality_gate_run_id=UUID("00000000-0000-0000-0000-000000000000"),
                severity=AnnotationQualityGateIssueSeverity(severity),
                code=code,
                message=message,
                split=split,
                image_path=image_path,
                annotation_ref=annotation_ref,
                details=details,
            )
        )
