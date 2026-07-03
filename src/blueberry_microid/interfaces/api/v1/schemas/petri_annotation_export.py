from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.petri_annotation_bbox_source import PetriAnnotationBboxSource
from blueberry_microid.domain.enums.petri_annotation_export_decision_filter import (
    PetriAnnotationExportDecisionFilter,
)
from blueberry_microid.domain.enums.petri_annotation_export_format import PetriAnnotationExportFormat
from blueberry_microid.domain.enums.petri_annotation_export_status import PetriAnnotationExportStatus


class PetriAnnotationExportConfigSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    export_format: PetriAnnotationExportFormat = PetriAnnotationExportFormat.BLUEBERRY_MANIFEST
    decision_filter: PetriAnnotationExportDecisionFilter = PetriAnnotationExportDecisionFilter.VALID_ONLY
    include_corrected_bbox: bool = True
    include_original_bbox: bool = True
    include_review_metadata: bool = True
    include_split: bool = True
    category_name: str = Field(default="candidate_region", min_length=1)
    category_id: int = Field(default=1, gt=0)
    normalize_yolo_coordinates: bool = True
    include_non_final_reviews: bool = False
    copy_images: bool = False
    output_dir: Optional[str] = None
    fail_on_missing_image_dimensions: bool = True


class PetriAnnotationExportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_release_id: UUID
    petri_segmentation_run_id: UUID
    config: PetriAnnotationExportConfigSchema = PetriAnnotationExportConfigSchema()
    created_by: Optional[str] = None
    notes: Optional[str] = None


class PetriAnnotationExportRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class PetriAnnotationExportItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class PetriAnnotationExportListResponse(BaseModel):
    exports: list[PetriAnnotationExportRunResponse]


class PetriAnnotationExportItemListResponse(BaseModel):
    items: list[PetriAnnotationExportItemResponse]
