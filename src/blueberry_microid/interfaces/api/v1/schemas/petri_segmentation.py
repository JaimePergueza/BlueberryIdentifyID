from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.petri_segmentation_status import PetriSegmentationStatus


class PetriSegmentationConfigRequest(BaseModel):
    algorithm: str = "classical_threshold"
    convert_to_grayscale: bool = True
    blur_enabled: bool = True
    blur_kernel_size: int = 5
    threshold_method: str = "otsu"
    manual_threshold: Optional[int] = None
    invert_threshold: bool = False
    morphological_opening: bool = True
    morphological_closing: bool = True
    morphology_kernel_size: int = 3
    min_region_area_px: int = 25
    max_region_area_px: Optional[int] = None
    min_circularity: Optional[float] = None
    exclude_border_regions: bool = False
    border_margin_px: int = 5
    max_regions: Optional[int] = None
    save_debug_masks: bool = False
    extraction_version: str = "petri_classical_v1"


class CreatePetriSegmentationRunRequestBody(BaseModel):
    dataset_release_id: UUID
    image_audit_run_id: Optional[UUID] = None
    petri_segmentation_config: PetriSegmentationConfigRequest = Field(default_factory=PetriSegmentationConfigRequest)
    created_by: Optional[str] = None
    notes: Optional[str] = None


class PetriSegmentationRegionResponse(BaseModel):
    id: UUID
    segmentation_run_id: UUID
    dataset_release_id: UUID
    dataset_item_id: UUID
    dataset_split_item_id: UUID
    split: DatasetSplit
    petri_image_path: str
    region_index: int
    area_px: float
    perimeter_px: Optional[float]
    centroid_x: float
    centroid_y: float
    bbox_x: int
    bbox_y: int
    bbox_width: int
    bbox_height: int
    circularity: Optional[float]
    solidity: Optional[float]
    mean_intensity: Optional[float]
    region_features: Optional[dict[str, Any]]
    created_at: datetime

    model_config = {"from_attributes": True}


class PetriSegmentationRunResponse(BaseModel):
    id: UUID
    dataset_release_id: UUID
    image_audit_run_id: Optional[UUID]
    status: PetriSegmentationStatus
    is_completed: bool
    config: dict[str, Any]
    total_items: int
    processed_petri_images: int
    failed_petri_images: int
    total_regions_detected: int
    mean_regions_per_image: Optional[float]
    summary: dict[str, Any]
    started_at: datetime
    completed_at: Optional[datetime]
    created_at: datetime
    created_by: Optional[str]
    notes: Optional[str]
    error_message: Optional[str]
    regions: list[PetriSegmentationRegionResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}
