from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from blueberry_microid.application.dto.detection_training_readiness_dto import (
    CreateDetectionTrainingReadinessReportRequest,
    DetectionTrainingReadinessReportDTO,
)
from blueberry_microid.application.exceptions import DetectionTrainingRunNotFoundError
from blueberry_microid.application.ports.annotation_bundle_file_repository import AnnotationBundleFileRepositoryPort
from blueberry_microid.application.ports.annotation_bundle_run_repository import AnnotationBundleRunRepositoryPort
from blueberry_microid.application.ports.annotation_quality_gate_issue_repository import (
    AnnotationQualityGateIssueRepositoryPort,
)
from blueberry_microid.application.ports.annotation_quality_gate_run_repository import (
    AnnotationQualityGateRunRepositoryPort,
)
from blueberry_microid.application.ports.detection_training_issue_repository import (
    DetectionTrainingIssueRepositoryPort,
)
from blueberry_microid.application.ports.detection_training_run_repository import DetectionTrainingRunRepositoryPort
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.application.services.detection_training_readiness_evaluator import (
    DetectionTrainingReadinessEvaluator,
)
from blueberry_microid.domain.entities.detection_training_readiness_issue import DetectionTrainingReadinessIssue
from blueberry_microid.domain.entities.detection_training_readiness_report import DetectionTrainingReadinessReport
from blueberry_microid.domain.enums.detection_training_readiness_decision import DetectionTrainingReadinessDecision
from blueberry_microid.domain.enums.detection_training_readiness_status import DetectionTrainingReadinessStatus


class CreateDetectionTrainingReadinessReportUseCase:
    """Evaluates whether a DetectionTrainingRun is ready for a future real
    training phase; never trains a model.

    Never modifies the referenced DetectionTrainingRun, AnnotationBundleRun,
    or AnnotationQualityGateRun, and never touches image or weight files.
    """

    def __init__(
        self,
        detection_training_run_repository: DetectionTrainingRunRepositoryPort,
        detection_training_issue_repository: DetectionTrainingIssueRepositoryPort,
        bundle_run_repository: AnnotationBundleRunRepositoryPort,
        bundle_file_repository: AnnotationBundleFileRepositoryPort,
        quality_gate_run_repository: AnnotationQualityGateRunRepositoryPort,
        quality_gate_issue_repository: AnnotationQualityGateIssueRepositoryPort,
        evaluator: DetectionTrainingReadinessEvaluator,
        unit_of_work: UnitOfWorkPort,
    ) -> None:
        self._detection_training_run_repository = detection_training_run_repository
        self._detection_training_issue_repository = detection_training_issue_repository
        self._bundle_run_repository = bundle_run_repository
        self._bundle_file_repository = bundle_file_repository
        self._quality_gate_run_repository = quality_gate_run_repository
        self._quality_gate_issue_repository = quality_gate_issue_repository
        self._evaluator = evaluator
        self._unit_of_work = unit_of_work

    def execute(
        self, request: CreateDetectionTrainingReadinessReportRequest
    ) -> DetectionTrainingReadinessReportDTO:
        run = self._detection_training_run_repository.get_by_id(request.detection_training_run_id)
        if run is None:
            raise DetectionTrainingRunNotFoundError(
                f"detection_training_run '{request.detection_training_run_id}' does not exist"
            )

        detection_training_issues = self._detection_training_issue_repository.list_by_detection_training_run_id(
            run.id
        )
        bundle_run = self._bundle_run_repository.get_by_id(run.annotation_bundle_run_id)
        bundle_files = (
            self._bundle_file_repository.list_by_bundle_run_id(bundle_run.id) if bundle_run is not None else []
        )
        quality_gate_run = (
            self._quality_gate_run_repository.get_by_id(run.annotation_quality_gate_run_id)
            if run.annotation_quality_gate_run_id is not None
            else None
        )
        quality_gate_issues = (
            self._quality_gate_issue_repository.list_by_quality_gate_run_id(quality_gate_run.id)
            if quality_gate_run is not None
            else []
        )

        config = request.config.to_config()
        now = datetime.now(timezone.utc)
        report_id = uuid4()

        try:
            evaluation = self._evaluator.evaluate(
                run,
                detection_training_issues,
                bundle_run,
                bundle_files,
                quality_gate_run,
                quality_gate_issues,
                config,
            )
            report = DetectionTrainingReadinessReport(
                id=report_id,
                detection_training_run_id=run.id,
                annotation_bundle_run_id=run.annotation_bundle_run_id,
                annotation_quality_gate_run_id=run.annotation_quality_gate_run_id,
                dataset_release_id=run.dataset_release_id,
                petri_annotation_export_run_id=run.petri_annotation_export_run_id,
                decision=evaluation.decision,
                status=evaluation.status,
                is_ready=evaluation.is_ready,
                config=config.to_dict(),
                data_summary=evaluation.data_summary,
                split_summary=evaluation.split_summary,
                quality_summary=evaluation.quality_summary,
                environment_summary=evaluation.environment_summary,
                contract_summary=evaluation.contract_summary,
                risk_summary=evaluation.risk_summary,
                recommendation_summary=evaluation.recommendation_summary,
                error_count=len(evaluation.errors),
                warning_count=len(evaluation.warnings),
                info_count=len(evaluation.infos),
                completed_at=now,
                created_by=request.created_by,
                notes=request.notes,
                error_message="; ".join(issue.message for issue in evaluation.errors[:3]) or None,
            )
            issues = [
                DetectionTrainingReadinessIssue(
                    id=issue.id,
                    readiness_report_id=report_id,
                    severity=issue.severity,
                    code=issue.code,
                    message=issue.message,
                    details=issue.details,
                    created_at=issue.created_at,
                )
                for issue in evaluation.issues
            ]
        except Exception as exc:  # noqa: BLE001 - any evaluation failure becomes a failed report
            report = DetectionTrainingReadinessReport(
                id=report_id,
                detection_training_run_id=run.id,
                annotation_bundle_run_id=run.annotation_bundle_run_id,
                annotation_quality_gate_run_id=run.annotation_quality_gate_run_id,
                dataset_release_id=run.dataset_release_id,
                petri_annotation_export_run_id=run.petri_annotation_export_run_id,
                decision=DetectionTrainingReadinessDecision.BLOCKED_BY_CONTRACT,
                status=DetectionTrainingReadinessStatus.FAILED,
                is_ready=False,
                config=config.to_dict(),
                data_summary={},
                split_summary={},
                quality_summary={},
                environment_summary={},
                contract_summary={},
                risk_summary={},
                recommendation_summary={},
                error_count=0,
                warning_count=0,
                info_count=0,
                completed_at=now,
                created_by=request.created_by,
                notes=request.notes,
                error_message=str(exc)[:2000],
            )
            issues = []

        with self._unit_of_work as uow:
            created = uow.detection_training_readiness_report_repository.add(report)
            if issues:
                uow.detection_training_readiness_issue_repository.add_many(issues)
            uow.commit()
        return DetectionTrainingReadinessReportDTO.from_entity(created)
