from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.image_dataset_audit_issue import ImageDatasetAuditIssue
from blueberry_microid.domain.entities.image_dataset_audit_run import ImageDatasetAuditRun
from blueberry_microid.domain.enums.image_dataset_audit_issue_severity import ImageDatasetAuditIssueSeverity
from blueberry_microid.domain.enums.image_dataset_audit_status import ImageDatasetAuditStatus
from blueberry_microid.domain.enums.image_modality import ImageModality
from blueberry_microid.ml.configs.image_audit_config import ImageAuditConfig


@dataclass(frozen=True, slots=True)
class CreateImageDatasetAuditRunRequest:
    dataset_release_id: UUID
    image_audit_config: ImageAuditConfig = field(default_factory=ImageAuditConfig)
    created_by: Optional[str] = None
    notes: Optional[str] = None


@dataclass(frozen=True, slots=True)
class ImageDatasetAuditIssueDTO:
    id: UUID
    audit_run_id: UUID
    severity: ImageDatasetAuditIssueSeverity
    modality: ImageModality
    code: str
    message: str
    dataset_item_id: Optional[UUID]
    dataset_split_item_id: Optional[UUID]
    image_path: Optional[str]
    details: Optional[dict]
    created_at: datetime

    @classmethod
    def from_entity(cls, issue: ImageDatasetAuditIssue) -> "ImageDatasetAuditIssueDTO":
        return cls(
            id=issue.id,
            audit_run_id=issue.audit_run_id,
            severity=issue.severity,
            modality=issue.modality,
            code=issue.code,
            message=issue.message,
            dataset_item_id=issue.dataset_item_id,
            dataset_split_item_id=issue.dataset_split_item_id,
            image_path=issue.image_path,
            details=issue.details,
            created_at=issue.created_at,
        )


@dataclass(frozen=True, slots=True)
class ImageDatasetAuditRunDTO:
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
    summary: dict
    format_distribution: dict
    color_mode_distribution: dict
    dimension_distribution: dict
    file_size_distribution: dict
    created_at: datetime
    created_by: Optional[str]
    notes: Optional[str]
    issues: list[ImageDatasetAuditIssueDTO] = field(default_factory=list)

    @classmethod
    def from_entity(
        cls,
        audit_run: ImageDatasetAuditRun,
        issues: Optional[list[ImageDatasetAuditIssue]] = None,
    ) -> "ImageDatasetAuditRunDTO":
        return cls(
            id=audit_run.id,
            dataset_release_id=audit_run.dataset_release_id,
            status=audit_run.status,
            is_passed=audit_run.is_passed,
            total_items=audit_run.total_items,
            total_petri_images=audit_run.total_petri_images,
            total_micro_images=audit_run.total_micro_images,
            checked_petri_images=audit_run.checked_petri_images,
            checked_micro_images=audit_run.checked_micro_images,
            failed_petri_images=audit_run.failed_petri_images,
            failed_micro_images=audit_run.failed_micro_images,
            warning_count=audit_run.warning_count,
            error_count=audit_run.error_count,
            summary=audit_run.summary,
            format_distribution=audit_run.format_distribution,
            color_mode_distribution=audit_run.color_mode_distribution,
            dimension_distribution=audit_run.dimension_distribution,
            file_size_distribution=audit_run.file_size_distribution,
            created_at=audit_run.created_at,
            created_by=audit_run.created_by,
            notes=audit_run.notes,
            issues=[ImageDatasetAuditIssueDTO.from_entity(issue) for issue in issues or []],
        )


def image_audit_config_to_dict(config: ImageAuditConfig) -> dict:
    return asdict(config)
