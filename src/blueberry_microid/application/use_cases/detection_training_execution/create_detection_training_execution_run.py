from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from blueberry_microid.application.dto.detection_training_execution_dto import (
    CreateDetectionTrainingExecutionRunRequest,
    DetectionTrainingExecutionRunDTO,
)
from blueberry_microid.application.exceptions import (
    DetectionTrainingArtifactPolicyNotFoundError,
    DetectionTrainingEnvironmentSpecNotFoundError,
    DetectionTrainingExecutionRunNotAllowedError,
    DetectionTrainingReadinessReportNotFoundError,
    DetectionTrainingRunNotFoundError,
)
from blueberry_microid.application.ports.detection_training_artifact_policy_repository import (
    DetectionTrainingArtifactPolicyRepositoryPort,
)
from blueberry_microid.application.ports.detection_training_environment_spec_repository import (
    DetectionTrainingEnvironmentSpecRepositoryPort,
)
from blueberry_microid.application.ports.detection_training_readiness_report_repository import (
    DetectionTrainingReadinessReportRepositoryPort,
)
from blueberry_microid.application.ports.detection_training_run_repository import DetectionTrainingRunRepositoryPort
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.application.services.detection_training_execution_gate_evaluator import (
    DetectionTrainingExecutionGateEvaluator,
)
from blueberry_microid.application.services.manual_yolo_training_runner_scaffold import (
    ManualYoloTrainingRunnerScaffold,
)
from blueberry_microid.domain.entities.detection_training_execution_issue import DetectionTrainingExecutionIssue
from blueberry_microid.domain.entities.detection_training_execution_run import DetectionTrainingExecutionRun
from blueberry_microid.domain.enums.detection_training_execution_decision import DetectionTrainingExecutionDecision
from blueberry_microid.domain.enums.detection_training_execution_mode import DetectionTrainingExecutionMode
from blueberry_microid.domain.enums.detection_training_execution_status import DetectionTrainingExecutionStatus
from blueberry_microid.ml.configs.repository_safety_config import RepositorySafetyConfig
from blueberry_microid.ml.validation.repository_safety_validator import RepositorySafetyValidator

_REPO_ROOT = Path(__file__).resolve().parents[5]


class CreateDetectionTrainingExecutionRunUseCase:
    """Evaluates and persists an execution-gate scaffold for a future,
    manually-triggered real training attempt; never trains a model.

    Never modifies the referenced DetectionTrainingRun,
    DetectionTrainingReadinessReport, DetectionTrainingEnvironmentSpec, or
    DetectionTrainingArtifactPolicy, and never writes files or executes a
    training command.
    """

    def __init__(
        self,
        detection_training_run_repository: DetectionTrainingRunRepositoryPort,
        readiness_report_repository: DetectionTrainingReadinessReportRepositoryPort,
        environment_spec_repository: DetectionTrainingEnvironmentSpecRepositoryPort,
        artifact_policy_repository: DetectionTrainingArtifactPolicyRepositoryPort,
        evaluator: DetectionTrainingExecutionGateEvaluator,
        scaffold: ManualYoloTrainingRunnerScaffold,
        unit_of_work: UnitOfWorkPort,
    ) -> None:
        self._detection_training_run_repository = detection_training_run_repository
        self._readiness_report_repository = readiness_report_repository
        self._environment_spec_repository = environment_spec_repository
        self._artifact_policy_repository = artifact_policy_repository
        self._evaluator = evaluator
        self._scaffold = scaffold
        self._unit_of_work = unit_of_work

    def execute(
        self, request: CreateDetectionTrainingExecutionRunRequest
    ) -> DetectionTrainingExecutionRunDTO:
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
            raise DetectionTrainingExecutionRunNotAllowedError(
                f"readiness_report '{readiness_report.id}' does not belong to detection_training_run '{run.id}'"
            )

        environment_spec = self._environment_spec_repository.get_by_id(request.environment_spec_id)
        if environment_spec is None:
            raise DetectionTrainingEnvironmentSpecNotFoundError(
                f"detection_training_environment_spec '{request.environment_spec_id}' does not exist"
            )
        if environment_spec.detection_training_run_id != run.id:
            raise DetectionTrainingExecutionRunNotAllowedError(
                f"environment_spec '{environment_spec.id}' does not belong to detection_training_run '{run.id}'"
            )
        if environment_spec.readiness_report_id != readiness_report.id:
            raise DetectionTrainingExecutionRunNotAllowedError(
                f"environment_spec '{environment_spec.id}' does not belong to readiness_report "
                f"'{readiness_report.id}'"
            )

        artifact_policy = self._artifact_policy_repository.get_by_id(request.artifact_policy_id)
        if artifact_policy is None:
            raise DetectionTrainingArtifactPolicyNotFoundError(
                f"detection_training_artifact_policy '{request.artifact_policy_id}' does not exist"
            )
        if artifact_policy.detection_training_run_id != run.id:
            raise DetectionTrainingExecutionRunNotAllowedError(
                f"artifact_policy '{artifact_policy.id}' does not belong to detection_training_run '{run.id}'"
            )
        if artifact_policy.readiness_report_id != readiness_report.id:
            raise DetectionTrainingExecutionRunNotAllowedError(
                f"artifact_policy '{artifact_policy.id}' does not belong to readiness_report "
                f"'{readiness_report.id}'"
            )
        if artifact_policy.environment_spec_id != environment_spec.id:
            raise DetectionTrainingExecutionRunNotAllowedError(
                f"artifact_policy '{artifact_policy.id}' does not belong to environment_spec "
                f"'{environment_spec.id}'"
            )

        config = request.config.to_config()
        now = datetime.now(timezone.utc)
        execution_run_id = uuid4()

        try:
            candidate_paths = [
                path
                for path in (run.expected_outputs or {}).values()
                if isinstance(path, str) and "://" not in path
            ]
            repository_safety_report = RepositorySafetyValidator().validate(
                repo_root=_REPO_ROOT,
                config=RepositorySafetyConfig(),
                candidate_paths=candidate_paths,
            )
            evaluation = self._evaluator.evaluate(
                run, readiness_report, environment_spec, artifact_policy, repository_safety_report, config
            )
            execution_plan = self._scaffold.build_execution_plan(evaluation)

            execution_run = DetectionTrainingExecutionRun(
                id=execution_run_id,
                detection_training_run_id=run.id,
                readiness_report_id=readiness_report.id,
                environment_spec_id=environment_spec.id,
                artifact_policy_id=artifact_policy.id,
                annotation_bundle_run_id=run.annotation_bundle_run_id,
                dataset_release_id=run.dataset_release_id,
                status=evaluation.status,
                decision=evaluation.decision,
                mode=config.mode,
                is_executable=False,
                config=config.to_dict(),
                prerequisite_summary=evaluation.prerequisite_summary,
                repository_safety_summary=evaluation.repository_safety_summary,
                execution_plan=execution_plan,
                command_preview=evaluation.command_preview,
                expected_outputs=evaluation.expected_outputs,
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
                DetectionTrainingExecutionIssue(
                    id=issue.id,
                    execution_run_id=execution_run_id,
                    severity=issue.severity,
                    code=issue.code,
                    message=issue.message,
                    details=issue.details,
                    created_at=issue.created_at,
                )
                for issue in evaluation.issues
            ]
        except Exception as exc:  # noqa: BLE001 - any evaluation failure becomes a failed execution run
            execution_run = DetectionTrainingExecutionRun(
                id=execution_run_id,
                detection_training_run_id=run.id,
                readiness_report_id=readiness_report.id,
                environment_spec_id=environment_spec.id,
                artifact_policy_id=artifact_policy.id,
                annotation_bundle_run_id=run.annotation_bundle_run_id,
                dataset_release_id=run.dataset_release_id,
                status=DetectionTrainingExecutionStatus.FAILED,
                decision=DetectionTrainingExecutionDecision.BLOCKED_BY_CONFIGURATION,
                mode=config.mode,
                is_executable=False,
                config=config.to_dict(),
                prerequisite_summary={},
                repository_safety_summary={},
                execution_plan={},
                command_preview={},
                expected_outputs={},
                risk_summary={},
                recommendation_summary={},
                error_count=1,
                warning_count=0,
                info_count=0,
                completed_at=now,
                created_by=request.created_by,
                notes=request.notes,
                error_message=str(exc)[:2000],
            )
            issues = []

        with self._unit_of_work as uow:
            created = uow.detection_training_execution_run_repository.add(execution_run)
            if issues:
                uow.detection_training_execution_issue_repository.add_many(issues)
            uow.commit()
        return DetectionTrainingExecutionRunDTO.from_entity(created)
