from __future__ import annotations

from uuid import UUID

from blueberry_microid.application.dto.image_audit_dto import (
    CreateImageDatasetAuditRunRequest,
    ImageDatasetAuditRunDTO,
)
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.application.services.dataset_release_manifest_exporter import DatasetReleaseManifestExporter
from blueberry_microid.domain.entities.image_dataset_audit_issue import ImageDatasetAuditIssue
from blueberry_microid.domain.entities.image_dataset_audit_run import ImageDatasetAuditRun
from blueberry_microid.ml.contracts.training_manifest import TrainingManifest
from blueberry_microid.ml.reports.image_audit_report import ImageAuditFinding
from blueberry_microid.ml.validation.image_dataset_auditor import ImageDatasetAuditor


class CreateImageDatasetAuditRunUseCase:
    """Audit the Petri/micro image files referenced by a DatasetRelease and
    persist the technical report.

    No model training, PyTorch, Celery, or tensor decoding happens here —
    this reuses the existing manifest exporter and a Pillow-based technical
    auditor, and stores the resulting report/issues transactionally.
    """

    def __init__(
        self,
        manifest_exporter: DatasetReleaseManifestExporter,
        image_dataset_auditor: ImageDatasetAuditor,
        unit_of_work: UnitOfWorkPort,
    ) -> None:
        self._manifest_exporter = manifest_exporter
        self._image_dataset_auditor = image_dataset_auditor
        self._unit_of_work = unit_of_work

    def execute(self, request: CreateImageDatasetAuditRunRequest) -> ImageDatasetAuditRunDTO:
        manifest_payload = self._manifest_exporter.export(request.dataset_release_id)
        manifest = TrainingManifest.from_dict(manifest_payload)
        report = self._image_dataset_auditor.audit(manifest, request.image_audit_config)

        summary = {
            "error_count": report.error_count,
            "warning_count": report.warning_count,
            "recommendations": report.recommendations,
            "contains_model_metrics": False,
            "contains_taxonomy": False,
        }

        audit_run = ImageDatasetAuditRun(
            dataset_release_id=UUID(manifest.dataset_release_id),
            status=report.status,
            is_passed=report.is_passed,
            total_items=report.total_items,
            total_petri_images=report.total_petri_images,
            total_micro_images=report.total_micro_images,
            checked_petri_images=report.checked_petri_images,
            checked_micro_images=report.checked_micro_images,
            failed_petri_images=report.failed_petri_images,
            failed_micro_images=report.failed_micro_images,
            warning_count=report.warning_count,
            error_count=report.error_count,
            summary=summary,
            format_distribution=report.format_distribution,
            color_mode_distribution=report.color_mode_distribution,
            dimension_distribution=report.dimension_distribution,
            file_size_distribution=report.file_size_distribution,
            created_by=request.created_by,
            notes=request.notes,
        )

        issues = [
            _finding_to_issue(finding, audit_run.id) for finding in (*report.errors, *report.warnings)
        ]

        with self._unit_of_work as uow:
            created_run = uow.image_dataset_audit_run_repository.add(audit_run)
            created_issues = uow.image_dataset_audit_issue_repository.add_many(issues) if issues else []
            uow.commit()

        return ImageDatasetAuditRunDTO.from_entity(created_run, created_issues)


def _finding_to_issue(finding: ImageAuditFinding, audit_run_id: UUID) -> ImageDatasetAuditIssue:
    return ImageDatasetAuditIssue(
        audit_run_id=audit_run_id,
        severity=finding.severity,
        modality=finding.modality,
        code=finding.code,
        message=finding.message,
        dataset_item_id=UUID(finding.dataset_item_id) if finding.dataset_item_id else None,
        dataset_split_item_id=UUID(finding.dataset_split_item_id) if finding.dataset_split_item_id else None,
        image_path=finding.image_path,
        details=finding.details,
    )
