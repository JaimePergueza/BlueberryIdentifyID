from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from blueberry_microid.application.dto.detection_training_artifact_dto import (
    CreateDetectionTrainingArtifactPolicyRequest,
    DetectionTrainingArtifactPolicyDTO,
)
from blueberry_microid.application.exceptions import (
    DetectionTrainingArtifactPolicyNotAllowedError,
    DetectionTrainingEnvironmentSpecNotFoundError,
    DetectionTrainingReadinessReportNotFoundError,
    DetectionTrainingRunNotFoundError,
)
from blueberry_microid.application.ports.annotation_bundle_file_repository import AnnotationBundleFileRepositoryPort
from blueberry_microid.application.ports.annotation_bundle_run_repository import AnnotationBundleRunRepositoryPort
from blueberry_microid.application.ports.detection_training_environment_spec_repository import (
    DetectionTrainingEnvironmentSpecRepositoryPort,
)
from blueberry_microid.application.ports.detection_training_readiness_report_repository import (
    DetectionTrainingReadinessReportRepositoryPort,
)
from blueberry_microid.application.ports.detection_training_run_repository import DetectionTrainingRunRepositoryPort
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.application.services.detection_training_artifact_policy_evaluator import (
    DetectionTrainingArtifactPolicyEvaluator,
)
from blueberry_microid.domain.entities.detection_training_artifact_issue import DetectionTrainingArtifactIssue
from blueberry_microid.domain.entities.detection_training_artifact_policy import DetectionTrainingArtifactPolicy
from blueberry_microid.domain.entities.detection_training_artifact_record import DetectionTrainingArtifactRecord
from blueberry_microid.domain.enums.detection_training_artifact_policy_decision import (
    DetectionTrainingArtifactPolicyDecision,
)
from blueberry_microid.domain.enums.detection_training_artifact_policy_status import (
    DetectionTrainingArtifactPolicyStatus,
)


class CreateDetectionTrainingArtifactPolicyUseCase:
    """Specifies/registers where a future real training attempt's artifacts
    would be stored for a DetectionTrainingRun; never trains a model.

    Never modifies the referenced DetectionTrainingRun,
    DetectionTrainingReadinessReport, DetectionTrainingEnvironmentSpec, or
    AnnotationBundleRun, and never writes artifact files.
    """

    def __init__(
        self,
        detection_training_run_repository: DetectionTrainingRunRepositoryPort,
        readiness_report_repository: DetectionTrainingReadinessReportRepositoryPort,
        environment_spec_repository: DetectionTrainingEnvironmentSpecRepositoryPort,
        bundle_run_repository: AnnotationBundleRunRepositoryPort,
        bundle_file_repository: AnnotationBundleFileRepositoryPort,
        evaluator: DetectionTrainingArtifactPolicyEvaluator,
        unit_of_work: UnitOfWorkPort,
    ) -> None:
        self._detection_training_run_repository = detection_training_run_repository
        self._readiness_report_repository = readiness_report_repository
        self._environment_spec_repository = environment_spec_repository
        self._bundle_run_repository = bundle_run_repository
        self._bundle_file_repository = bundle_file_repository
        self._evaluator = evaluator
        self._unit_of_work = unit_of_work

    def execute(
        self, request: CreateDetectionTrainingArtifactPolicyRequest
    ) -> DetectionTrainingArtifactPolicyDTO:
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
            raise DetectionTrainingArtifactPolicyNotAllowedError(
                f"readiness_report '{readiness_report.id}' does not belong to detection_training_run '{run.id}'"
            )

        environment_spec = self._environment_spec_repository.get_by_id(request.environment_spec_id)
        if environment_spec is None:
            raise DetectionTrainingEnvironmentSpecNotFoundError(
                f"detection_training_environment_spec '{request.environment_spec_id}' does not exist"
            )
        if environment_spec.detection_training_run_id != run.id:
            raise DetectionTrainingArtifactPolicyNotAllowedError(
                f"environment_spec '{environment_spec.id}' does not belong to detection_training_run '{run.id}'"
            )
        if environment_spec.readiness_report_id != readiness_report.id:
            raise DetectionTrainingArtifactPolicyNotAllowedError(
                f"environment_spec '{environment_spec.id}' does not belong to readiness_report "
                f"'{readiness_report.id}'"
            )

        bundle_run = self._bundle_run_repository.get_by_id(run.annotation_bundle_run_id)
        bundle_files = (
            self._bundle_file_repository.list_by_bundle_run_id(bundle_run.id) if bundle_run is not None else []
        )

        config = request.config.to_config()
        now = datetime.now(timezone.utc)
        policy_id = uuid4()

        try:
            evaluation = self._evaluator.evaluate(run, environment_spec, bundle_run, bundle_files, config)
            policy = DetectionTrainingArtifactPolicy(
                id=policy_id,
                detection_training_run_id=run.id,
                readiness_report_id=readiness_report.id,
                environment_spec_id=environment_spec.id,
                annotation_bundle_run_id=run.annotation_bundle_run_id,
                dataset_release_id=run.dataset_release_id,
                decision=evaluation.decision,
                status=evaluation.status,
                is_policy_ready=evaluation.is_policy_ready,
                config=config.to_dict(),
                artifact_root_dir=config.artifact_root_dir,
                planned_output_summary=evaluation.planned_output_summary,
                storage_policy=evaluation.storage_policy,
                git_policy=evaluation.git_policy,
                checksum_policy=evaluation.checksum_policy,
                registry_summary=evaluation.registry_summary,
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
            records = [
                DetectionTrainingArtifactRecord(
                    id=record.id,
                    artifact_policy_id=policy_id,
                    detection_training_run_id=record.detection_training_run_id,
                    artifact_kind=record.artifact_kind,
                    artifact_state=record.artifact_state,
                    location_type=record.location_type,
                    artifact_path=record.artifact_path,
                    relative_path=record.relative_path,
                    external_uri=record.external_uri,
                    file_extension=record.file_extension,
                    size_bytes=record.size_bytes,
                    checksum_sha256=record.checksum_sha256,
                    metadata=record.metadata,
                    created_at=record.created_at,
                )
                for record in evaluation.artifact_records
            ]
            issues = [
                DetectionTrainingArtifactIssue(
                    id=issue.id,
                    artifact_policy_id=policy_id,
                    severity=issue.severity,
                    code=issue.code,
                    message=issue.message,
                    artifact_path=issue.artifact_path,
                    details=issue.details,
                    created_at=issue.created_at,
                )
                for issue in evaluation.issues
            ]
        except Exception as exc:  # noqa: BLE001 - any evaluation failure becomes a failed policy
            policy = DetectionTrainingArtifactPolicy(
                id=policy_id,
                detection_training_run_id=run.id,
                readiness_report_id=readiness_report.id,
                environment_spec_id=environment_spec.id,
                annotation_bundle_run_id=run.annotation_bundle_run_id,
                dataset_release_id=run.dataset_release_id,
                decision=DetectionTrainingArtifactPolicyDecision.BLOCKED_BY_ENVIRONMENT,
                status=DetectionTrainingArtifactPolicyStatus.FAILED,
                is_policy_ready=False,
                config=config.to_dict(),
                artifact_root_dir=config.artifact_root_dir,
                planned_output_summary={},
                storage_policy={},
                git_policy={},
                checksum_policy={},
                registry_summary={},
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
            records = []
            issues = []

        with self._unit_of_work as uow:
            created = uow.detection_training_artifact_policy_repository.add(policy)
            if records:
                uow.detection_training_artifact_record_repository.add_many(records)
            if issues:
                uow.detection_training_artifact_issue_repository.add_many(issues)
            uow.commit()
        return DetectionTrainingArtifactPolicyDTO.from_entity(created)
