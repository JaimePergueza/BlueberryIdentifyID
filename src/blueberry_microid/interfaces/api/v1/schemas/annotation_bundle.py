from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from blueberry_microid.domain.enums.annotation_bundle_file_role import AnnotationBundleFileRole
from blueberry_microid.domain.enums.annotation_bundle_status import AnnotationBundleStatus


class AnnotationBundleConfigSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output_dir: Optional[str] = None
    dry_run: bool = True
    copy_images: bool = False
    overwrite_existing: bool = False
    include_coco: bool = True
    include_yolo: bool = True
    include_blueberry_manifest: bool = True
    include_dataset_yaml: bool = True
    include_readme: bool = True
    validate_before_write: bool = True
    fail_on_invalid_bbox: bool = True
    fail_on_missing_image: bool = False
    preserve_split_dirs: bool = True
    bundle_name: Optional[str] = None
    relative_image_paths: bool = True


class AnnotationBundleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    petri_annotation_export_run_id: UUID
    config: AnnotationBundleConfigSchema = AnnotationBundleConfigSchema()
    created_by: Optional[str] = None
    notes: Optional[str] = None


class AnnotationBundleRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    petri_annotation_export_run_id: UUID
    dataset_release_id: UUID
    petri_segmentation_run_id: UUID
    status: AnnotationBundleStatus
    is_completed: bool
    config: dict
    output_dir: Optional[str]
    dry_run: bool
    file_count: int
    annotation_count: int
    image_count: int
    label_count: int
    validation_summary: dict
    bundle_manifest: dict
    created_at: datetime
    completed_at: Optional[datetime]
    created_by: Optional[str]
    notes: Optional[str]
    error_message: Optional[str]


class AnnotationBundleFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bundle_run_id: UUID
    file_role: AnnotationBundleFileRole
    file_path: str
    relative_path: str
    content_type: Optional[str]
    size_bytes: Optional[int]
    checksum_sha256: Optional[str]
    created_at: datetime


class AnnotationBundleListResponse(BaseModel):
    bundles: list[AnnotationBundleRunResponse]


class AnnotationBundleFileListResponse(BaseModel):
    files: list[AnnotationBundleFileResponse]
