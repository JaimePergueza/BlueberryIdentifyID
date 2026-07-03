from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.annotation_bundle_file import AnnotationBundleFile
from blueberry_microid.domain.entities.annotation_bundle_run import AnnotationBundleRun
from blueberry_microid.domain.enums.annotation_bundle_file_role import AnnotationBundleFileRole
from blueberry_microid.domain.enums.annotation_bundle_status import AnnotationBundleStatus
from blueberry_microid.ml.configs.annotation_bundle_config import AnnotationBundleConfig


@dataclass(frozen=True)
class AnnotationBundleConfigDTO:
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

    def to_config(self) -> AnnotationBundleConfig:
        return AnnotationBundleConfig(**self.__dict__)


@dataclass(frozen=True)
class CreateAnnotationBundleRunRequest:
    petri_annotation_export_run_id: UUID
    config: AnnotationBundleConfigDTO = AnnotationBundleConfigDTO()
    created_by: Optional[str] = None
    notes: Optional[str] = None


@dataclass(frozen=True)
class AnnotationBundleRunDTO:
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

    @classmethod
    def from_entity(cls, run: AnnotationBundleRun) -> "AnnotationBundleRunDTO":
        return cls(
            id=run.id,
            petri_annotation_export_run_id=run.petri_annotation_export_run_id,
            dataset_release_id=run.dataset_release_id,
            petri_segmentation_run_id=run.petri_segmentation_run_id,
            status=run.status,
            is_completed=run.is_completed,
            config=run.config,
            output_dir=run.output_dir,
            dry_run=run.dry_run,
            file_count=run.file_count,
            annotation_count=run.annotation_count,
            image_count=run.image_count,
            label_count=run.label_count,
            validation_summary=run.validation_summary,
            bundle_manifest=run.bundle_manifest,
            created_at=run.created_at,
            completed_at=run.completed_at,
            created_by=run.created_by,
            notes=run.notes,
            error_message=run.error_message,
        )


@dataclass(frozen=True)
class AnnotationBundleFileDTO:
    id: UUID
    bundle_run_id: UUID
    file_role: AnnotationBundleFileRole
    file_path: str
    relative_path: str
    content_type: Optional[str]
    size_bytes: Optional[int]
    checksum_sha256: Optional[str]
    created_at: datetime

    @classmethod
    def from_entity(cls, file: AnnotationBundleFile) -> "AnnotationBundleFileDTO":
        return cls(
            id=file.id,
            bundle_run_id=file.bundle_run_id,
            file_role=file.file_role,
            file_path=file.file_path,
            relative_path=file.relative_path,
            content_type=file.content_type,
            size_bytes=file.size_bytes,
            checksum_sha256=file.checksum_sha256,
            created_at=file.created_at,
        )
