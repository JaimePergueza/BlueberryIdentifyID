from __future__ import annotations

import re
from uuid import UUID

from blueberry_microid.application.dto.ml_preflight_dto import (
    CreateTrainingPreflightRunRequest,
    TrainingPreflightRunDTO,
    training_config_to_dict,
)
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.application.services.dataset_release_manifest_exporter import DatasetReleaseManifestExporter
from blueberry_microid.domain.entities.training_preflight_issue import TrainingPreflightIssue
from blueberry_microid.domain.entities.training_preflight_run import TrainingPreflightRun
from blueberry_microid.domain.enums.training_preflight_issue_severity import TrainingPreflightIssueSeverity
from blueberry_microid.domain.enums.training_preflight_status import TrainingPreflightStatus
from blueberry_microid.ml.contracts.training_manifest import TrainingManifest
from blueberry_microid.ml.reports.validation_report import ManifestValidationReport
from blueberry_microid.ml.validation.image_path_validator import ImagePathValidator
from blueberry_microid.ml.validation.manifest_validator import ManifestValidator


class CreateTrainingPreflightRunUseCase:
    """Validate a DatasetRelease manifest and persist the preflight report.

    No model training, PyTorch, performance metrics, Celery, or image decoding
    happens here. The use case only reuses Fase 11 validators and stores their
    report transactionally.
    """

    def __init__(
        self,
        manifest_exporter: DatasetReleaseManifestExporter,
        manifest_validator: ManifestValidator,
        image_path_validator: ImagePathValidator,
        unit_of_work: UnitOfWorkPort,
    ) -> None:
        self._manifest_exporter = manifest_exporter
        self._manifest_validator = manifest_validator
        self._image_path_validator = image_path_validator
        self._unit_of_work = unit_of_work

    def execute(self, request: CreateTrainingPreflightRunRequest) -> TrainingPreflightRunDTO:
        manifest_payload = self._manifest_exporter.export(request.dataset_release_id)
        manifest = TrainingManifest.from_dict(manifest_payload)
        report = self._manifest_validator.validate(manifest, request.training_config)

        image_path_errors: list[str] = []
        if request.validate_image_paths:
            image_path_report = self._image_path_validator.validate(manifest)
            image_path_errors = image_path_report.errors

        errors = [*report.errors, *image_path_errors]
        warnings = report.warnings
        is_valid = len(errors) == 0
        status = _status_for(is_valid, warnings)
        summary = _build_summary(report, errors, warnings, request.validate_image_paths)
        recommendation_summary = "; ".join(report.recommendations) if report.recommendations else None

        preflight_run = TrainingPreflightRun(
            dataset_release_id=UUID(manifest.dataset_release_id),
            status=status,
            is_valid=is_valid,
            config=training_config_to_dict(request.training_config),
            summary=summary,
            item_count=report.item_count,
            train_count=report.split_counts.get("train", 0),
            validation_count=report.split_counts.get("validation", 0),
            test_count=report.split_counts.get("test", 0),
            label_counts=report.label_counts,
            split_counts=report.split_counts,
            split_label_counts=report.split_label_counts,
            leakage_checks=report.leakage_checks,
            recommendation_summary=recommendation_summary,
            created_by=request.created_by,
            notes=request.notes,
        )

        issues = [
            *_issues_from_messages(
                errors,
                TrainingPreflightIssueSeverity.ERROR,
                "manifest_validation_error",
                preflight_run.id,
            ),
            *_issues_from_messages(
                warnings,
                TrainingPreflightIssueSeverity.WARNING,
                "manifest_validation_warning",
                preflight_run.id,
            ),
        ]

        with self._unit_of_work as uow:
            created_run = uow.training_preflight_run_repository.add(preflight_run)
            created_issues = uow.training_preflight_issue_repository.add_many(issues) if issues else []
            uow.commit()

        return TrainingPreflightRunDTO.from_entity(created_run, created_issues)


def _status_for(is_valid: bool, warnings: list[str]) -> TrainingPreflightStatus:
    if not is_valid:
        return TrainingPreflightStatus.FAILED
    if warnings:
        return TrainingPreflightStatus.WARNING
    return TrainingPreflightStatus.PASSED


def _build_summary(
    report: ManifestValidationReport,
    errors: list[str],
    warnings: list[str],
    validate_image_paths: bool,
) -> dict:
    return {
        "error_count": len(errors),
        "warning_count": len(warnings),
        "validate_image_paths": validate_image_paths,
        "recommendations": report.recommendations,
        "contains_model_metrics": False,
    }


def _issues_from_messages(
    messages: list[str],
    severity: TrainingPreflightIssueSeverity,
    code: str,
    preflight_run_id: UUID,
) -> list[TrainingPreflightIssue]:
    return [
        TrainingPreflightIssue(
            preflight_run_id=preflight_run_id,
            severity=severity,
            code=code,
            message=message,
            field=_extract_field(message),
            item_ref=_extract_item_ref(message),
        )
        for message in messages
    ]


def _extract_item_ref(message: str) -> str | None:
    match = re.search(r"item\[\d+\]", message)
    return match.group(0) if match else None


def _extract_field(message: str) -> str | None:
    for field in (
        "petri_image_path",
        "micro_image_path",
        "ground_truth_label",
        "split",
        "sample_id",
        "lot_code",
        "origin",
        "analysis_run_id",
    ):
        if field in message:
            return field
    return None
