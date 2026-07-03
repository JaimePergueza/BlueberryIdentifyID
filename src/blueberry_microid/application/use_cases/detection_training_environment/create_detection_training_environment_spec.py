from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from blueberry_microid.application.dto.detection_training_environment_dto import (
    CreateDetectionTrainingEnvironmentSpecRequest,
    DetectionTrainingEnvironmentSpecDTO,
)
from blueberry_microid.application.exceptions import (
    DetectionTrainingEnvironmentNotAllowedError,
    DetectionTrainingReadinessReportNotFoundError,
    DetectionTrainingRunNotFoundError,
)
from blueberry_microid.application.ports.annotation_bundle_file_repository import AnnotationBundleFileRepositoryPort
from blueberry_microid.application.ports.annotation_bundle_run_repository import AnnotationBundleRunRepositoryPort
from blueberry_microid.application.ports.detection_training_readiness_report_repository import (
    DetectionTrainingReadinessReportRepositoryPort,
)
from blueberry_microid.application.ports.detection_training_run_repository import DetectionTrainingRunRepositoryPort
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.application.services.detection_training_environment_evaluator import (
    DetectionTrainingEnvironmentEvaluator,
)
from blueberry_microid.domain.entities.detection_training_environment_issue import (
    DetectionTrainingEnvironmentIssue,
)
from blueberry_microid.domain.entities.detection_training_environment_spec import DetectionTrainingEnvironmentSpec
from blueberry_microid.domain.enums.detection_training_environment_decision import (
    DetectionTrainingEnvironmentDecision,
)
from blueberry_microid.domain.enums.detection_training_environment_status import DetectionTrainingEnvironmentStatus


class CreateDetectionTrainingEnvironmentSpecUseCase:
    """Specifies/evaluates the environment a future real training attempt for
    a DetectionTrainingRun would run in; never trains a model.

    Never modifies the referenced DetectionTrainingRun,
    DetectionTrainingReadinessReport, or AnnotationBundleRun, and never
    installs dependencies, downloads weights, or touches image files.
    """

    def __init__(
        self,
        detection_training_run_repository: DetectionTrainingRunRepositoryPort,
        readiness_report_repository: DetectionTrainingReadinessReportRepositoryPort,
        bundle_run_repository: AnnotationBundleRunRepositoryPort,
        bundle_file_repository: AnnotationBundleFileRepositoryPort,
        evaluator: DetectionTrainingEnvironmentEvaluator,
        unit_of_work: UnitOfWorkPort,
    ) -> None:
        self._detection_training_run_repository = detection_training_run_repository
        self._readiness_report_repository = readiness_report_repository
        self._bundle_run_repository = bundle_run_repository
        self._bundle_file_repository = bundle_file_repository
        self._evaluator = evaluator
        self._unit_of_work = unit_of_work

    def execute(
        self, request: CreateDetectionTrainingEnvironmentSpecRequest
    ) -> DetectionTrainingEnvironmentSpecDTO:
        run = self._detection_training_run_repository.get_by_id(request.detection_training_run_id)
        if run is None:
            raise DetectionTrainingRunNotFoundError(
                f"detection_training_run '{request.detection_training_run_id}' does not exist"
            )

        readiness_report = self._readiness_report_repository.get_by_id(request.readiness_report_id)
        if readiness_report is None:
            raise DetectionTrainingReadinessReportNotFoundError(
                f"detection_training_readiness_report '{request.readiness_report_id}' does not exist"
            )
        if readiness_report.detection_training_run_id != run.id:
            raise DetectionTrainingEnvironmentNotAllowedError(
                f"readiness_report '{readiness_report.id}' does not belong to detection_training_run '{run.id}'"
            )

        bundle_run = self._bundle_run_repository.get_by_id(run.annotation_bundle_run_id)
        bundle_files = (
            self._bundle_file_repository.list_by_bundle_run_id(bundle_run.id) if bundle_run is not None else []
        )

        config = request.config.to_config()
        now = datetime.now(timezone.utc)
        spec_id = uuid4()

        try:
            evaluation = self._evaluator.evaluate(
                run,
                readiness_report,
                [],
                bundle_run,
                bundle_files,
                config,
            )
            spec = DetectionTrainingEnvironmentSpec(
                id=spec_id,
                detection_training_run_id=run.id,
                readiness_report_id=readiness_report.id,
                annotation_bundle_run_id=run.annotation_bundle_run_id,
                dataset_release_id=run.dataset_release_id,
                decision=evaluation.decision,
                status=evaluation.status,
                is_environment_ready=evaluation.is_environment_ready,
                config=config.to_dict(),
                detected_environment=evaluation.detected_environment,
                dependency_policy=evaluation.dependency_policy,
                hardware_policy=evaluation.hardware_policy,
                artifact_policy=evaluation.artifact_policy,
                execution_policy=evaluation.execution_policy,
                setup_instructions=evaluation.setup_instructions,
                safe_check_summary=evaluation.safe_check_summary,
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
                DetectionTrainingEnvironmentIssue(
                    id=issue.id,
                    environment_spec_id=spec_id,
                    severity=issue.severity,
                    code=issue.code,
                    message=issue.message,
                    details=issue.details,
                    created_at=issue.created_at,
                )
                for issue in evaluation.issues
            ]
        except Exception as exc:  # noqa: BLE001 - any evaluation failure becomes a failed spec
            spec = DetectionTrainingEnvironmentSpec(
                id=spec_id,
                detection_training_run_id=run.id,
                readiness_report_id=readiness_report.id,
                annotation_bundle_run_id=run.annotation_bundle_run_id,
                dataset_release_id=run.dataset_release_id,
                decision=DetectionTrainingEnvironmentDecision.BLOCKED_BY_MISSING_REQUIREMENTS,
                status=DetectionTrainingEnvironmentStatus.FAILED,
                is_environment_ready=False,
                config=config.to_dict(),
                detected_environment={},
                dependency_policy={},
                hardware_policy={},
                artifact_policy={},
                execution_policy={},
                setup_instructions={},
                safe_check_summary={},
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
            created = uow.detection_training_environment_spec_repository.add(spec)
            if issues:
                uow.detection_training_environment_issue_repository.add_many(issues)
            uow.commit()
        return DetectionTrainingEnvironmentSpecDTO.from_entity(created)
