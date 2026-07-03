from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.annotation_quality_gate_issue import AnnotationQualityGateIssue
from blueberry_microid.domain.entities.annotation_quality_gate_run import AnnotationQualityGateRun
from blueberry_microid.domain.enums.annotation_quality_gate_issue_severity import (
    AnnotationQualityGateIssueSeverity,
)
from blueberry_microid.domain.enums.annotation_quality_gate_status import AnnotationQualityGateStatus
from blueberry_microid.ml.configs.annotation_quality_gate_config import AnnotationQualityGateConfig


@dataclass(frozen=True)
class AnnotationQualityGateConfigDTO:
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
    allowed_splits: Optional[list[str]] = None
    allowed_categories: Optional[list[str]] = None

    def to_config(self) -> AnnotationQualityGateConfig:
        values = self.__dict__.copy()
        if values["allowed_splits"] is None:
            values.pop("allowed_splits")
        if values["allowed_categories"] is None:
            values.pop("allowed_categories")
        return AnnotationQualityGateConfig(**values)


@dataclass(frozen=True)
class CreateAnnotationQualityGateRunRequest:
    annotation_bundle_run_id: UUID
    config: AnnotationQualityGateConfigDTO = AnnotationQualityGateConfigDTO()
    created_by: Optional[str] = None
    notes: Optional[str] = None


@dataclass(frozen=True)
class AnnotationQualityGateRunDTO:
    id: UUID
    annotation_bundle_run_id: UUID
    dataset_release_id: UUID
    petri_annotation_export_run_id: UUID
    status: AnnotationQualityGateStatus
    is_passed: bool
    config: dict
    total_images: int
    total_annotations: int
    train_image_count: int
    validation_image_count: int
    test_image_count: int
    train_annotation_count: int
    validation_annotation_count: int
    test_annotation_count: int
    error_count: int
    warning_count: int
    quality_summary: dict
    split_distribution: dict
    bbox_statistics: dict
    category_distribution: dict
    created_at: datetime
    completed_at: Optional[datetime]
    created_by: Optional[str]
    notes: Optional[str]
    error_message: Optional[str]

    @classmethod
    def from_entity(cls, run: AnnotationQualityGateRun) -> "AnnotationQualityGateRunDTO":
        return cls(**run.__dict__)


@dataclass(frozen=True)
class AnnotationQualityGateIssueDTO:
    id: UUID
    quality_gate_run_id: UUID
    severity: AnnotationQualityGateIssueSeverity
    code: str
    message: str
    split: Optional[str]
    image_path: Optional[str]
    annotation_ref: Optional[str]
    details: Optional[dict]
    created_at: datetime

    @classmethod
    def from_entity(cls, issue: AnnotationQualityGateIssue) -> "AnnotationQualityGateIssueDTO":
        return cls(**issue.__dict__)
