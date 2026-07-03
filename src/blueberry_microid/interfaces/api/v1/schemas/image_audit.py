from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from blueberry_microid.domain.enums.image_dataset_audit_issue_severity import ImageDatasetAuditIssueSeverity
from blueberry_microid.domain.enums.image_dataset_audit_status import ImageDatasetAuditStatus
from blueberry_microid.domain.enums.image_modality import ImageModality


class ImageAuditConfigRequest(BaseModel):
    validate_existence: bool = True
    validate_readability: bool = True
    validate_format: bool = True
    validate_dimensions: bool = True
    validate_color_mode: bool = True
    validate_file_size: bool = True
    detect_duplicate_paths: bool = True
    min_width: int = 64
    min_height: int = 64
    max_width: Optional[int] = None
    max_height: Optional[int] = None
    max_file_size_bytes: Optional[int] = None
    allowed_formats: list[str] = Field(default_factory=lambda: ["JPEG", "PNG", "WEBP"])
    allowed_color_modes: list[str] = Field(default_factory=lambda: ["RGB", "RGBA", "L"])
    warn_on_dimension_outliers: bool = True


class CreateImageDatasetAuditRunRequestBody(BaseModel):
    dataset_release_id: UUID
    image_audit_config: ImageAuditConfigRequest = Field(default_factory=ImageAuditConfigRequest)
    created_by: Optional[str] = None
    notes: Optional[str] = None


class ImageDatasetAuditIssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    audit_run_id: UUID
    severity: ImageDatasetAuditIssueSeverity
    modality: ImageModality
    code: str
    message: str
    dataset_item_id: Optional[UUID]
    dataset_split_item_id: Optional[UUID]
    image_path: Optional[str]
    details: Optional[dict[str, Any]]
    created_at: datetime


class ImageDatasetAuditRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_release_id: UUID
    status: ImageDatasetAuditStatus
    is_passed: bool
    total_items: int
    total_petri_images: int
    total_micro_images: int
    checked_petri_images: int
    checked_micro_images: int
    failed_petri_images: int
    failed_micro_images: int
    warning_count: int
    error_count: int
    summary: dict[str, Any]
    format_distribution: dict[str, int]
    color_mode_distribution: dict[str, int]
    dimension_distribution: dict[str, int]
    file_size_distribution: dict[str, int]
    created_at: datetime
    created_by: Optional[str]
    notes: Optional[str]
    issues: list[ImageDatasetAuditIssueResponse] = Field(default_factory=list)
