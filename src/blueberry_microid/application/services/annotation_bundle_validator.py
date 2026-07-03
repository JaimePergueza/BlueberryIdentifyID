from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from blueberry_microid.domain.entities.petri_annotation_export_item import PetriAnnotationExportItem
from blueberry_microid.domain.entities.petri_annotation_export_run import PetriAnnotationExportRun
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.ml.configs.annotation_bundle_config import AnnotationBundleConfig


_FORBIDDEN_TERMS = ("bacteria", "fungi", "fungus", "colony", "species", "genus", "taxon", "diagnosis")


@dataclass(frozen=True)
class AnnotationBundleValidationReport:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    annotation_count: int = 0
    image_count: int = 0
    split_counts: dict[str, int] = field(default_factory=dict)
    format_checks: dict[str, bool] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "annotation_count": self.annotation_count,
            "image_count": self.image_count,
            "split_counts": self.split_counts,
            "format_checks": self.format_checks,
            "recommendations": self.recommendations,
        }


class AnnotationBundleValidator:
    """Validate persisted annotation export data before bundle writing."""

    def validate(
        self,
        export_run: PetriAnnotationExportRun,
        items: list[PetriAnnotationExportItem],
        config: AnnotationBundleConfig,
    ) -> AnnotationBundleValidationReport:
        errors: list[str] = []
        warnings: list[str] = []
        manifest = export_run.output_manifest or {}
        format_checks = {
            "blueberry_manifest": self._validate_blueberry_manifest(manifest, errors),
            "coco_json": self._validate_coco(manifest, errors),
            "yolo_txt": self._validate_yolo(manifest, errors),
        }

        if not manifest:
            errors.append("output_manifest is empty")
        manifest_label_payload = " ".join(self._manifest_label_values(manifest)).lower()
        if any(term in manifest_label_payload for term in _FORBIDDEN_TERMS):
            errors.append("forbidden taxonomy-like term found in output_manifest")
        if export_run.exported_annotation_count > 0 and not items:
            errors.append("export_run reports annotations but no export items were found")
        if not items:
            warnings.append("annotation export contains zero bundleable annotations")

        split_counts: dict[str, int] = {}
        image_paths: set[str] = set()
        for item in items:
            if item.bbox_width <= 0:
                errors.append(f"bbox_width must be positive for export item {item.id}")
            if item.bbox_height <= 0:
                errors.append(f"bbox_height must be positive for export item {item.id}")
            if item.bbox_x < 0 or item.bbox_y < 0:
                errors.append(f"bbox x/y must be non-negative for export item {item.id}")
            if item.split not in set(DatasetSplit):
                errors.append(f"invalid split for export item {item.id}: {item.split}")
            label_payload = (item.export_label + " " + str(item.export_payload)).lower()
            if any(term in label_payload for term in _FORBIDDEN_TERMS):
                errors.append(f"taxonomy or diagnosis term found in export item {item.id}")
            if config.fail_on_missing_image and not Path(item.petri_image_path).exists():
                errors.append(f"missing image path: {item.petri_image_path}")
            split_counts[item.split.value] = split_counts.get(item.split.value, 0) + 1
            image_paths.add(item.petri_image_path)

        recommendations = []
        if config.copy_images:
            recommendations.append("copy_images is not supported in this phase; keep external image references")
        if config.dry_run:
            recommendations.append("dry_run completed without writing files")

        return AnnotationBundleValidationReport(
            is_valid=not errors,
            errors=errors,
            warnings=warnings,
            annotation_count=len(items),
            image_count=len(image_paths),
            split_counts=split_counts,
            format_checks=format_checks,
            recommendations=recommendations,
        )

    @staticmethod
    def _validate_blueberry_manifest(manifest: dict, errors: list[str]) -> bool:
        if "annotations" not in manifest:
            return False
        for annotation in manifest.get("annotations", []):
            bbox = annotation.get("bbox")
            if not (isinstance(bbox, list) and len(bbox) == 4):
                errors.append("blueberry_manifest annotation bbox must be [x, y, width, height]")
                return False
            if bbox[0] < 0 or bbox[1] < 0 or bbox[2] <= 0 or bbox[3] <= 0:
                errors.append("blueberry_manifest annotation bbox has invalid coordinates")
                return False
        return True

    @staticmethod
    def _validate_coco(manifest: dict, errors: list[str]) -> bool:
        if not {"images", "annotations", "categories"}.issubset(manifest):
            return False
        image_ids = [image.get("id") for image in manifest.get("images", [])]
        annotation_ids = [annotation.get("id") for annotation in manifest.get("annotations", [])]
        if len(image_ids) != len(set(image_ids)):
            errors.append("COCO images must have unique ids")
            return False
        if len(annotation_ids) != len(set(annotation_ids)):
            errors.append("COCO annotations must have unique ids")
            return False
        category_ids = {category.get("id") for category in manifest.get("categories", [])}
        for annotation in manifest.get("annotations", []):
            bbox = annotation.get("bbox")
            if not (isinstance(bbox, list) and len(bbox) == 4):
                errors.append("COCO bbox must be [x, y, width, height]")
                return False
            if bbox[0] < 0 or bbox[1] < 0 or bbox[2] <= 0 or bbox[3] <= 0:
                errors.append("COCO bbox has invalid coordinates")
                return False
            if annotation.get("area", 0) <= 0:
                errors.append("COCO annotation area must be positive")
                return False
            if annotation.get("category_id") not in category_ids:
                errors.append("COCO annotation category_id is not declared")
                return False
        return True

    @staticmethod
    def _validate_yolo(manifest: dict, errors: list[str]) -> bool:
        if "labels" not in manifest:
            return False
        for label in manifest.get("labels", []):
            for line in label.get("lines", []):
                parts = line.split()
                if len(parts) != 5:
                    errors.append("YOLO label line must have 5 fields")
                    return False
                try:
                    class_id = int(parts[0])
                    coords = [float(value) for value in parts[1:]]
                except ValueError:
                    errors.append("YOLO label fields must be numeric")
                    return False
                if class_id < 0:
                    errors.append("YOLO class_id must be non-negative")
                    return False
                if not all(0.0 <= value <= 1.0 for value in coords):
                    errors.append("YOLO coordinates must be normalized between 0 and 1")
                    return False
                if coords[2] <= 0.0 or coords[3] <= 0.0:
                    errors.append("YOLO normalized width/height must be positive")
                    return False
        return True

    @classmethod
    def _manifest_label_values(cls, value: Any) -> list[str]:
        if isinstance(value, dict):
            found: list[str] = []
            for key, nested in value.items():
                if key in {"label", "name", "category"} and isinstance(nested, (str, int, float)):
                    found.append(str(nested))
                else:
                    found.extend(cls._manifest_label_values(nested))
            return found
        if isinstance(value, list):
            found: list[str] = []
            for nested in value:
                found.extend(cls._manifest_label_values(nested))
            return found
        return []
