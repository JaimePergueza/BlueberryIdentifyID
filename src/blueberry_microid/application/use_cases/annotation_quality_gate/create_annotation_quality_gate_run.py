from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from blueberry_microid.application.dto.annotation_quality_gate_dto import (
    AnnotationQualityGateRunDTO,
    CreateAnnotationQualityGateRunRequest,
)
from blueberry_microid.application.exceptions import (
    AnnotationBundleRunNotFoundError,
    AnnotationQualityGateNotAllowedError,
)
from blueberry_microid.application.ports.annotation_bundle_file_repository import AnnotationBundleFileRepositoryPort
from blueberry_microid.application.ports.annotation_bundle_run_repository import AnnotationBundleRunRepositoryPort
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.application.services.annotation_quality_gate_validator import AnnotationQualityGateValidator
from blueberry_microid.domain.entities.annotation_quality_gate_issue import AnnotationQualityGateIssue
from blueberry_microid.domain.entities.annotation_quality_gate_run import AnnotationQualityGateRun


class CreateAnnotationQualityGateRunUseCase:
    def __init__(
        self,
        bundle_run_repository: AnnotationBundleRunRepositoryPort,
        bundle_file_repository: AnnotationBundleFileRepositoryPort,
        validator: AnnotationQualityGateValidator,
        unit_of_work: UnitOfWorkPort,
    ) -> None:
        self._bundle_run_repository = bundle_run_repository
        self._bundle_file_repository = bundle_file_repository
        self._validator = validator
        self._unit_of_work = unit_of_work

    def execute(self, request: CreateAnnotationQualityGateRunRequest) -> AnnotationQualityGateRunDTO:
        bundle_run = self._bundle_run_repository.get_by_id(request.annotation_bundle_run_id)
        if bundle_run is None:
            raise AnnotationBundleRunNotFoundError(
                f"annotation_bundle_run '{request.annotation_bundle_run_id}' does not exist"
            )
        try:
            config = request.config.to_config()
        except ValueError as exc:
            raise AnnotationQualityGateNotAllowedError(str(exc)) from exc

        bundle_files = self._bundle_file_repository.list_by_bundle_run_id(bundle_run.id)
        report = self._validator.validate(bundle_run, bundle_files, config)
        now = datetime.now(timezone.utc)
        gate_run_id = uuid4()
        split = report.split_distribution
        gate_run = AnnotationQualityGateRun(
            id=gate_run_id,
            annotation_bundle_run_id=bundle_run.id,
            dataset_release_id=bundle_run.dataset_release_id,
            petri_annotation_export_run_id=bundle_run.petri_annotation_export_run_id,
            status=report.status,
            is_passed=report.is_passed,
            config=config.to_dict(),
            total_images=report.total_images,
            total_annotations=report.total_annotations,
            train_image_count=split.get("train", {}).get("images", 0),
            validation_image_count=split.get("validation", {}).get("images", 0),
            test_image_count=split.get("test", {}).get("images", 0),
            train_annotation_count=split.get("train", {}).get("annotations", 0),
            validation_annotation_count=split.get("validation", {}).get("annotations", 0),
            test_annotation_count=split.get("test", {}).get("annotations", 0),
            error_count=len(report.errors),
            warning_count=len(report.warnings),
            quality_summary=report.summary(),
            split_distribution=report.split_distribution,
            bbox_statistics=report.bbox_statistics,
            category_distribution=report.category_distribution,
            completed_at=now,
            created_by=request.created_by,
            notes=request.notes,
            error_message="; ".join(issue.message for issue in report.errors[:3]) if report.errors else None,
        )
        issues = [
            AnnotationQualityGateIssue(
                id=issue.id,
                quality_gate_run_id=gate_run_id,
                severity=issue.severity,
                code=issue.code,
                message=issue.message,
                split=issue.split,
                image_path=issue.image_path,
                annotation_ref=issue.annotation_ref,
                details=issue.details,
                created_at=issue.created_at,
            )
            for issue in report.issues
        ]

        with self._unit_of_work as uow:
            created = uow.annotation_quality_gate_run_repository.add(gate_run)
            if issues:
                uow.annotation_quality_gate_issue_repository.add_many(issues)
            uow.commit()
        return AnnotationQualityGateRunDTO.from_entity(created)
