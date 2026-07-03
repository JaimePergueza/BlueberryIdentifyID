from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


_FORBIDDEN_TERMS = ("bacteria", "fungi", "fungus", "colony", "species", "genus", "taxon", "diagnosis")


@dataclass(frozen=True)
class AnnotationQualityGateConfig:
    require_completed_bundle: bool = True
    validate_files_exist: bool = True
    validate_coco: bool = True
    validate_yolo: bool = True
    validate_blueberry_manifest: bool = True
    validate_dataset_yaml: bool = True
    min_total_images: int = 1
    min_total_annotations: int = 1
    min_images_per_split: int = 0
    min_annotations_per_split: int = 0
    min_bbox_width_px: int = 2
    min_bbox_height_px: int = 2
    max_bbox_area_ratio: Optional[float] = None
    min_bbox_area_ratio: Optional[float] = None
    fail_on_empty_split: bool = True
    fail_on_images_without_annotations: bool = False
    warn_on_images_without_annotations: bool = True
    fail_on_duplicate_bboxes: bool = False
    warn_on_duplicate_bboxes: bool = True
    fail_on_single_class: bool = False
    warn_on_single_class: bool = True
    allowed_splits: list[str] = field(default_factory=lambda: ["train", "validation", "test"])
    allowed_categories: list[str] = field(default_factory=lambda: ["candidate_region"])

    def __post_init__(self) -> None:
        if self.min_total_images < 1:
            raise ValueError("min_total_images must be >= 1")
        if self.min_total_annotations < 0:
            raise ValueError("min_total_annotations must be >= 0")
        if self.min_images_per_split < 0:
            raise ValueError("min_images_per_split must be >= 0")
        if self.min_annotations_per_split < 0:
            raise ValueError("min_annotations_per_split must be >= 0")
        if self.min_bbox_width_px <= 0:
            raise ValueError("min_bbox_width_px must be > 0")
        if self.min_bbox_height_px <= 0:
            raise ValueError("min_bbox_height_px must be > 0")
        if self.min_bbox_area_ratio is not None and self.min_bbox_area_ratio < 0:
            raise ValueError("min_bbox_area_ratio must be >= 0 when provided")
        if self.max_bbox_area_ratio is not None and self.max_bbox_area_ratio <= 0:
            raise ValueError("max_bbox_area_ratio must be > 0 when provided")
        if self.min_bbox_area_ratio is not None and self.max_bbox_area_ratio is not None:
            if self.min_bbox_area_ratio > self.max_bbox_area_ratio:
                raise ValueError("min_bbox_area_ratio cannot exceed max_bbox_area_ratio")
        for split in self.allowed_splits:
            if split not in {"train", "validation", "test"}:
                raise ValueError(f"unsupported split: {split}")
        for category in self.allowed_categories:
            lowered = category.lower()
            if any(term in lowered for term in _FORBIDDEN_TERMS):
                raise ValueError("allowed_categories cannot include taxonomy or diagnosis terms")

    def to_dict(self) -> dict:
        return {
            "require_completed_bundle": self.require_completed_bundle,
            "validate_files_exist": self.validate_files_exist,
            "validate_coco": self.validate_coco,
            "validate_yolo": self.validate_yolo,
            "validate_blueberry_manifest": self.validate_blueberry_manifest,
            "validate_dataset_yaml": self.validate_dataset_yaml,
            "min_total_images": self.min_total_images,
            "min_total_annotations": self.min_total_annotations,
            "min_images_per_split": self.min_images_per_split,
            "min_annotations_per_split": self.min_annotations_per_split,
            "min_bbox_width_px": self.min_bbox_width_px,
            "min_bbox_height_px": self.min_bbox_height_px,
            "max_bbox_area_ratio": self.max_bbox_area_ratio,
            "min_bbox_area_ratio": self.min_bbox_area_ratio,
            "fail_on_empty_split": self.fail_on_empty_split,
            "fail_on_images_without_annotations": self.fail_on_images_without_annotations,
            "warn_on_images_without_annotations": self.warn_on_images_without_annotations,
            "fail_on_duplicate_bboxes": self.fail_on_duplicate_bboxes,
            "warn_on_duplicate_bboxes": self.warn_on_duplicate_bboxes,
            "fail_on_single_class": self.fail_on_single_class,
            "warn_on_single_class": self.warn_on_single_class,
            "allowed_splits": list(self.allowed_splits),
            "allowed_categories": list(self.allowed_categories),
        }
