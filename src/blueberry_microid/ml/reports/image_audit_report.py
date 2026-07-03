from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from blueberry_microid.domain.enums.image_dataset_audit_issue_severity import ImageDatasetAuditIssueSeverity
from blueberry_microid.domain.enums.image_dataset_audit_status import ImageDatasetAuditStatus
from blueberry_microid.domain.enums.image_modality import ImageModality


@dataclass(frozen=True, slots=True)
class ImageAuditFinding:
    """One technical finding for a single Petri or micro image file.

    Reused as-is by `CreateImageDatasetAuditRunUseCase` to build persisted
    `ImageDatasetAuditIssue` rows — it carries everything an issue needs
    except the audit_run_id, which only exists once the run itself has been
    created.
    """

    severity: ImageDatasetAuditIssueSeverity
    modality: ImageModality
    code: str
    message: str
    dataset_item_id: Optional[str] = None
    dataset_split_item_id: Optional[str] = None
    image_path: Optional[str] = None
    details: Optional[dict] = None


@dataclass(frozen=True, slots=True)
class ImageDatasetAuditReport:
    """Result of running `ImageDatasetAuditor` over one DatasetRelease
    manifest. Technical file-level findings only — never model performance
    metrics, never a taxonomic/microbiological judgment."""

    is_passed: bool
    status: ImageDatasetAuditStatus
    total_items: int = 0
    total_petri_images: int = 0
    total_micro_images: int = 0
    checked_petri_images: int = 0
    checked_micro_images: int = 0
    failed_petri_images: int = 0
    failed_micro_images: int = 0
    errors: list[ImageAuditFinding] = field(default_factory=list)
    warnings: list[ImageAuditFinding] = field(default_factory=list)
    format_distribution: dict[str, int] = field(default_factory=dict)
    color_mode_distribution: dict[str, int] = field(default_factory=dict)
    dimension_distribution: dict[str, int] = field(default_factory=dict)
    file_size_distribution: dict[str, int] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)
