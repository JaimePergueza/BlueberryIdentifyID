from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.petri_annotation_export_item import PetriAnnotationExportItem
from blueberry_microid.domain.entities.petri_annotation_export_run import PetriAnnotationExportRun
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.petri_annotation_bbox_source import PetriAnnotationBboxSource
from blueberry_microid.domain.enums.petri_annotation_export_decision_filter import (
    PetriAnnotationExportDecisionFilter,
)
from blueberry_microid.domain.enums.petri_annotation_export_format import PetriAnnotationExportFormat
from blueberry_microid.domain.enums.petri_annotation_export_status import PetriAnnotationExportStatus
from blueberry_microid.ml.configs.petri_annotation_export_config import PetriAnnotationExportConfig


@dataclass(frozen=True)
class PetriAnnotationExportConfigDTO:
    export_format: PetriAnnotationExportFormat = PetriAnnotationExportFormat.BLUEBERRY_MANIFEST
    decision_filter: PetriAnnotationExportDecisionFilter = PetriAnnotationExportDecisionFilter.VALID_ONLY
    include_corrected_bbox: bool = True
    include_original_bbox: bool = True
    include_review_metadata: bool = True
    include_split: bool = True
    category_name: str = "candidate_region"
    category_id: int = 1
    normalize_yolo_coordinates: bool = True
    include_non_final_reviews: bool = False
    copy_images: bool = False
    output_dir: Optional[str] = None
    fail_on_missing_image_dimensions: bool = True

    def to_config(self) -> PetriAnnotationExportConfig:
        return PetriAnnotationExportConfig(
            export_format=self.export_format,
            decision_filter=self.decision_filter,
            include_corrected_bbox=self.include_corrected_bbox,
            include_original_bbox=self.include_original_bbox,
            include_review_metadata=self.include_review_metadata,
            include_split=self.include_split,
            category_name=self.category_name,
            category_id=self.category_id,
            normalize_yolo_coordinates=self.normalize_yolo_coordinates,
            include_non_final_reviews=self.include_non_final_reviews,
            copy_images=self.copy_images,
            output_dir=self.output_dir,
            fail_on_missing_image_dimensions=self.fail_on_missing_image_dimensions,
        )


@dataclass(frozen=True)
class CreatePetriAnnotationExportRunRequest:
    dataset_release_id: UUID
    petri_segmentation_run_id: UUID
    config: PetriAnnotationExportConfigDTO = PetriAnnotationExportConfigDTO()
    created_by: Optional[str] = None
    notes: Optional[str] = None


@dataclass(frozen=True)
class PetriAnnotationExportRunDTO:
    id: UUID
    dataset_release_id: UUID
    petri_segmentation_run_id: UUID
    export_format: PetriAnnotationExportFormat
    status: PetriAnnotationExportStatus
    is_completed: bool
    config: dict
    exported_annotation_count: int
    skipped_review_count: int
    image_count: int
    category_count: int
    output_manifest: dict
    summary: dict
    created_at: datetime
    completed_at: Optional[datetime]
    created_by: Optional[str]
    notes: Optional[str]
    error_message: Optional[str]

    @classmethod
    def from_entity(cls, run: PetriAnnotationExportRun) -> "PetriAnnotationExportRunDTO":
        return cls(
            id=run.id,
            dataset_release_id=run.dataset_release_id,
            petri_segmentation_run_id=run.petri_segmentation_run_id,
            export_format=run.export_format,
            status=run.status,
            is_completed=run.is_completed,
            config=run.config,
            exported_annotation_count=run.exported_annotation_count,
            skipped_review_count=run.skipped_review_count,
            image_count=run.image_count,
            category_count=run.category_count,
            output_manifest=run.output_manifest,
            summary=run.summary,
            created_at=run.created_at,
            completed_at=run.completed_at,
            created_by=run.created_by,
            notes=run.notes,
            error_message=run.error_message,
        )


@dataclass(frozen=True)
class PetriAnnotationExportItemDTO:
    id: UUID
    export_run_id: UUID
    petri_region_review_id: UUID
    petri_segmentation_region_id: UUID
    dataset_release_id: UUID
    dataset_item_id: UUID
    dataset_split_item_id: UUID
    split: DatasetSplit
    petri_image_path: str
    export_label: str
    bbox_x: int
    bbox_y: int
    bbox_width: int
    bbox_height: int
    bbox_source: PetriAnnotationBboxSource
    export_payload: dict
    created_at: datetime

    @classmethod
    def from_entity(cls, item: PetriAnnotationExportItem) -> "PetriAnnotationExportItemDTO":
        return cls(
            id=item.id,
            export_run_id=item.export_run_id,
            petri_region_review_id=item.petri_region_review_id,
            petri_segmentation_region_id=item.petri_segmentation_region_id,
            dataset_release_id=item.dataset_release_id,
            dataset_item_id=item.dataset_item_id,
            dataset_split_item_id=item.dataset_split_item_id,
            split=item.split,
            petri_image_path=item.petri_image_path,
            export_label=item.export_label,
            bbox_x=item.bbox_x,
            bbox_y=item.bbox_y,
            bbox_width=item.bbox_width,
            bbox_height=item.bbox_height,
            bbox_source=item.bbox_source,
            export_payload=item.export_payload,
            created_at=item.created_at,
        )
