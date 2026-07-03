from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.image_feature_extraction_status import ImageFeatureExtractionStatus
from blueberry_microid.domain.enums.image_modality import ImageModality


class ImageFeatureExtractionConfigRequest(BaseModel):
    require_audit_passed: bool = True
    allow_audit_warning: bool = True
    convert_to_rgb: bool = True
    resize_enabled: bool = False
    resize_width: Optional[int] = None
    resize_height: Optional[int] = None
    compute_basic_geometry: bool = True
    compute_intensity_features: bool = True
    compute_color_features: bool = True
    compute_sharpness_features: bool = True
    compute_texture_features: bool = True
    compute_histogram_features: bool = True
    histogram_bins: int = 16
    max_image_pixels: Optional[int] = None
    fail_on_unreadable_image: bool = True


class CreateImageFeatureExtractionRunRequestBody(BaseModel):
    dataset_release_id: UUID
    image_audit_run_id: UUID
    config: ImageFeatureExtractionConfigRequest = Field(default_factory=ImageFeatureExtractionConfigRequest)
    created_by: Optional[str] = None
    notes: Optional[str] = None


class ImageFeatureVectorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    feature_extraction_run_id: UUID
    dataset_release_id: UUID
    dataset_item_id: UUID
    dataset_split_item_id: UUID
    split: DatasetSplit
    modality: ImageModality
    image_path: str
    features: dict[str, Any]
    preprocessing: dict[str, Any]
    extraction_version: str
    created_at: datetime


class ImageFeatureExtractionRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_release_id: UUID
    image_audit_run_id: UUID
    status: ImageFeatureExtractionStatus
    is_completed: bool
    config: dict[str, Any]
    total_items: int
    processed_items: int
    failed_items: int
    total_feature_vectors: int
    petri_feature_count: int
    micro_feature_count: int
    summary: dict[str, Any]
    started_at: datetime
    completed_at: Optional[datetime]
    created_at: datetime
    created_by: Optional[str]
    notes: Optional[str]
    error_message: Optional[str]
    vectors: list[ImageFeatureVectorResponse] = Field(default_factory=list)
