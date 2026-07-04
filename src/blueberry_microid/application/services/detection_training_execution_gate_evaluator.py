from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import UUID

from blueberry_microid.domain.entities.detection_training_artifact_policy import DetectionTrainingArtifactPolicy
from blueberry_microid.domain.entities.detection_training_environment_spec import DetectionTrainingEnvironmentSpec
from blueberry_microid.domain.entities.detection_training_execution_issue import DetectionTrainingExecutionIssue
from blueberry_microid.domain.entities.detection_training_readiness_report import DetectionTrainingReadinessReport
from blueberry_microid.domain.entities.detection_training_run import DetectionTrainingRun
from blueberry_microid.domain.enums.detection_training_artifact_policy_decision import (
    DetectionTrainingArtifactPolicyDecision,
)
from blueberry_microid.domain.enums.detection_training_artifact_policy_status import (
    DetectionTrainingArtifactPolicyStatus,
)
from blueberry_microid.domain.enums.detection_training_environment_decision import (
    DetectionTrainingEnvironmentDecision,
)
from blueberry_microid.domain.enums.detection_training_environment_status import DetectionTrainingEnvironmentStatus
from blueberry_microid.domain.enums.detection_training_execution_decision import DetectionTrainingExecutionDecision
from blueberry_microid.domain.enums.detection_training_execution_issue_severity import (
    DetectionTrainingExecutionIssueSeverity,
)
from blueberry_microid.domain.enums.detection_training_execution_status import DetectionTrainingExecutionStatus
from blueberry_microid.domain.enums.detection_training_readiness_decision import DetectionTrainingReadinessDecision
from blueberry_microid.domain.enums.detection_training_readiness_status import DetectionTrainingReadinessStatus
from blueberry_microid.domain.enums.detection_training_status import DetectionTrainingStatus
from blueberry_microid.ml.configs.detection_training_execution_config import DetectionTrainingExecutionConfig
from blueberry_microid.ml.reports.repository_safety_report import RepositorySafetyReport

_PLACEHOLDER_RUN_ID = UUID("00000000-0000-0000-0000-000000000000")

_PREREQUISITE_CODES = {
    "detection_training_not_planned",
    "command_preview_missing",
    "expected_outputs_missing",
}
_READINESS_CODES = {"readiness_report_missing", "readiness_not_ready"}
_ENVIRONMENT_CODES = {"environment_spec_missing", "environment_not_ready"}
_ARTIFACT_POLICY_CODES = {"artifact_policy_missing", "artifact_policy_not_ready"}
_REPOSITORY_SAFETY_CODES = {"repository_safety_failed", "artifact_root_not_safe"}
_CI_CODES = {"ci_execution_blocked"}
_CONFIGURATION_CODES = {"training_execution_disabled"}

_ACCEPTABLE_READINESS_DECISIONS = {DetectionTrainingReadinessDecision.READY_FOR_TRAINING}
_ACCEPTABLE_ENVIRONMENT_DECISIONS = {DetectionTrainingEnvironmentDecision.ENVIRONMENT_READY}
_ACCEPTABLE_ARTIFACT_POLICY_DECISIONS = {DetectionTrainingArtifactPolicyDecision.ARTIFACT_POLICY_READY}


def _running_in_ci() -> bool:
    return bool(os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"))


@dataclass(frozen=True)
class DetectionTrainingExecutionGateEvaluation:
    status: DetectionTrainingExecutionStatus
    decision: DetectionTrainingExecutionDecision
    is_executable: bool
    prerequisite_summary: dict[str, Any]
    repository_safety_summary: dict[str, Any]
    execution_plan: dict[str, Any]
    command_preview: dict[str, Any]
    expected_outputs: dict[str, Any]
    risk_summary: dict[str, Any]
    recommendation_summary: dict[str, Any]
    issues: list[DetectionTrainingExecutionIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[DetectionTrainingExecutionIssue]:
        return [issue for issue in self.issues if issue.severity == DetectionTrainingExecutionIssueSeverity.ERROR]

    @property
    def warnings(self) -> list[DetectionTrainingExecutionIssue]:
        return [issue for issue in self.issues if issue.severity == DetectionTrainingExecutionIssueSeverity.WARNING]

    @property
    def infos(self) -> list[DetectionTrainingExecutionIssue]:
        return [issue for issue in self.issues if issue.severity == DetectionTrainingExecutionIssueSeverity.INFO]


class DetectionTrainingExecutionGateEvaluator:
    """Evaluates whether a future, manually-triggered real training attempt
    is blocked, requires manual confirmation, or has passed every configured
    prerequisite gate.

    Purely an inspection of already-persisted metadata plus a
    already-computed `RepositorySafetyReport`. Never calls `subprocess`,
    never imports `torch`/`ultralytics`, never installs dependencies, never
    modifies files, never creates weights, never downloads anything, and
    never executes a training command — this phase has no code path that
    does any of that.
    """

    def evaluate(
        self,
        detection_training_run: DetectionTrainingRun,
        readiness_report: Optional[DetectionTrainingReadinessReport],
        environment_spec: Optional[DetectionTrainingEnvironmentSpec],
        artifact_policy: Optional[DetectionTrainingArtifactPolicy],
        repository_safety_report: RepositorySafetyReport,
        config: DetectionTrainingExecutionConfig,
    ) -> DetectionTrainingExecutionGateEvaluation:
        issues: list[DetectionTrainingExecutionIssue] = []

        self._evaluate_run_prerequisites(detection_training_run, config, issues)
        self._evaluate_readiness(readiness_report, config, issues)
        self._evaluate_environment(environment_spec, config, issues)
        self._evaluate_artifact_policy(artifact_policy, config, issues)
        self._evaluate_repository_safety(repository_safety_report, artifact_policy, config, issues)
        self._evaluate_ci(config, issues)
        self._evaluate_real_training_flags(config, issues)

        self._issue(issues, "info", "no_training_executed", "no training command was executed by this evaluation")
        self._issue(
            issues,
            "info",
            "real_runner_not_implemented",
            "no real training executor exists yet; this phase only produces a manual scaffold",
        )

        confirmation_status = self._confirmation_status(config, issues)

        error_codes = {issue.code for issue in issues if issue.severity == DetectionTrainingExecutionIssueSeverity.ERROR}
        has_blocking_errors = bool(error_codes)

        if has_blocking_errors:
            status = DetectionTrainingExecutionStatus.BLOCKED
        elif confirmation_status == "missing_or_invalid":
            status = DetectionTrainingExecutionStatus.MANUAL_REQUIRED
        elif not config.allow_ready_to_execute_status:
            status = DetectionTrainingExecutionStatus.MANUAL_REQUIRED
        else:
            status = DetectionTrainingExecutionStatus.READY_TO_EXECUTE

        decision = self._decision(error_codes, status)
        is_executable = False

        prerequisite_summary = self._prerequisite_summary(detection_training_run, readiness_report, environment_spec)
        repository_safety_summary = self._repository_safety_summary(repository_safety_report)
        expected_outputs = dict(detection_training_run.expected_outputs or {})
        command_preview = dict(detection_training_run.command_preview or {})
        risk_summary = self._risk_summary(issues)
        recommendation_summary = self._recommendation_summary(error_codes, confirmation_status, status)
        execution_plan = {
            "status": status.value,
            "decision": decision.value,
            "note": "execution_plan is enriched by ManualYoloTrainingRunnerScaffold before persistence",
        }

        return DetectionTrainingExecutionGateEvaluation(
            status=status,
            decision=decision,
            is_executable=is_executable,
            prerequisite_summary=prerequisite_summary,
            repository_safety_summary=repository_safety_summary,
            execution_plan=execution_plan,
            command_preview=command_preview,
            expected_outputs=expected_outputs,
            risk_summary=risk_summary,
            recommendation_summary=recommendation_summary,
            issues=issues,
        )

    # -- A. DetectionTrainingRun -------------------------------------------

    def _evaluate_run_prerequisites(
        self,
        run: DetectionTrainingRun,
        config: DetectionTrainingExecutionConfig,
        issues: list[DetectionTrainingExecutionIssue],
    ) -> None:
        if config.require_detection_training_planned and run.status != DetectionTrainingStatus.PLANNED:
            self._issue(
                issues,
                "error",
                "detection_training_not_planned",
                f"detection_training_run status is '{run.status.value}', not 'planned'",
            )
        if not run.is_runnable:
            self._issue(
                issues,
                "error",
                "detection_training_not_planned",
                "detection_training_run.is_runnable is false",
            )
        if config.require_command_preview and not run.command_preview:
            self._issue(
                issues, "error", "command_preview_missing", "detection_training_run has no command_preview"
            )
        if config.require_expected_outputs and not run.expected_outputs:
            self._issue(
                issues, "error", "expected_outputs_missing", "detection_training_run has no expected_outputs"
            )

    # -- B. ReadinessReport --------------------------------------------------

    def _evaluate_readiness(
        self,
        readiness_report: Optional[DetectionTrainingReadinessReport],
        config: DetectionTrainingExecutionConfig,
        issues: list[DetectionTrainingExecutionIssue],
    ) -> None:
        if readiness_report is None:
            self._issue(issues, "error", "readiness_report_missing", "no DetectionTrainingReadinessReport provided")
            return
        if config.require_readiness_ready and readiness_report.decision not in _ACCEPTABLE_READINESS_DECISIONS:
            self._issue(
                issues,
                "error",
                "readiness_not_ready",
                f"readiness_report decision is '{readiness_report.decision.value}', not 'ready_for_training'",
            )
        elif readiness_report.status not in {
            DetectionTrainingReadinessStatus.READY,
            DetectionTrainingReadinessStatus.WARNING,
        }:
            self._issue(
                issues,
                "error",
                "readiness_not_ready",
                f"readiness_report status is '{readiness_report.status.value}'",
            )

    # -- C. EnvironmentSpec ----------------------------------------------------

    def _evaluate_environment(
        self,
        environment_spec: Optional[DetectionTrainingEnvironmentSpec],
        config: DetectionTrainingExecutionConfig,
        issues: list[DetectionTrainingExecutionIssue],
    ) -> None:
        if environment_spec is None:
            self._issue(issues, "error", "environment_spec_missing", "no DetectionTrainingEnvironmentSpec provided")
            return
        if config.require_environment_ready and environment_spec.decision not in _ACCEPTABLE_ENVIRONMENT_DECISIONS:
            self._issue(
                issues,
                "error",
                "environment_not_ready",
                f"environment_spec decision is '{environment_spec.decision.value}', not 'environment_ready'",
            )
        elif environment_spec.status not in {
            DetectionTrainingEnvironmentStatus.READY,
            DetectionTrainingEnvironmentStatus.WARNING,
        }:
            self._issue(
                issues,
                "error",
                "environment_not_ready",
                f"environment_spec status is '{environment_spec.status.value}'",
            )

    # -- D. ArtifactPolicy -----------------------------------------------------

    def _evaluate_artifact_policy(
        self,
        artifact_policy: Optional[DetectionTrainingArtifactPolicy],
        config: DetectionTrainingExecutionConfig,
        issues: list[DetectionTrainingExecutionIssue],
    ) -> None:
        if artifact_policy is None:
            self._issue(issues, "error", "artifact_policy_missing", "no DetectionTrainingArtifactPolicy provided")
            return
        if (
            config.require_artifact_policy_ready
            and artifact_policy.decision not in _ACCEPTABLE_ARTIFACT_POLICY_DECISIONS
        ):
            self._issue(
                issues,
                "error",
                "artifact_policy_not_ready",
                f"artifact_policy decision is '{artifact_policy.decision.value}', not 'artifact_policy_ready'",
            )
        elif artifact_policy.status not in {
            DetectionTrainingArtifactPolicyStatus.READY,
            DetectionTrainingArtifactPolicyStatus.WARNING,
        }:
            self._issue(
                issues,
                "error",
                "artifact_policy_not_ready",
                f"artifact_policy status is '{artifact_policy.status.value}'",
            )

    # -- E. RepositorySafety -----------------------------------------------------

    def _evaluate_repository_safety(
        self,
        repository_safety_report: RepositorySafetyReport,
        artifact_policy: Optional[DetectionTrainingArtifactPolicy],
        config: DetectionTrainingExecutionConfig,
        issues: list[DetectionTrainingExecutionIssue],
    ) -> None:
        if config.require_repository_safety_passed and not repository_safety_report.is_safe:
            self._issue(
                issues,
                "error",
                "repository_safety_failed",
                "RepositorySafetyValidator reported the repository is not safe for future training artifacts",
                details={
                    "missing_gitignore_patterns": list(repository_safety_report.missing_gitignore_patterns),
                    "path_violations": [
                        {"path": v.path, "extension": v.extension} for v in repository_safety_report.path_violations
                    ],
                },
            )
        if artifact_policy is not None and artifact_policy.storage_policy.get("artifact_root_dir_inside_repo"):
            self._issue(
                issues,
                "error",
                "artifact_root_not_safe",
                "artifact_policy.artifact_root_dir resolves inside the repository",
                details={"artifact_root_dir": artifact_policy.artifact_root_dir},
            )

    # -- F. CI --------------------------------------------------------------

    def _evaluate_ci(
        self, config: DetectionTrainingExecutionConfig, issues: list[DetectionTrainingExecutionIssue]
    ) -> None:
        if config.block_in_ci and _running_in_ci():
            self._issue(
                issues,
                "error",
                "ci_execution_blocked",
                "execution is blocked because this evaluation is running inside a CI environment",
            )

    # -- H. Real training flags ----------------------------------------------

    def _evaluate_real_training_flags(
        self, config: DetectionTrainingExecutionConfig, issues: list[DetectionTrainingExecutionIssue]
    ) -> None:
        if config.enable_real_training:
            self._issue(
                issues,
                "error",
                "training_execution_disabled",
                "enable_real_training=true is not supported in this phase; real training is always disabled",
            )
        if not config.dry_run_only:
            self._issue(
                issues,
                "error",
                "training_execution_disabled",
                "dry_run_only=false is not supported in this phase; only dry-run scaffolding is allowed",
            )

    # -- G. Manual confirmation ----------------------------------------------

    def _confirmation_status(
        self, config: DetectionTrainingExecutionConfig, issues: list[DetectionTrainingExecutionIssue]
    ) -> str:
        if not config.require_manual_confirmation:
            return "not_required"
        if not config.manual_confirmation_text:
            self._issue(
                issues,
                "warning",
                "manual_confirmation_missing",
                "require_manual_confirmation=true but manual_confirmation_text was not provided",
            )
            return "missing_or_invalid"
        if config.manual_confirmation_text != config.required_confirmation_text:
            self._issue(
                issues,
                "warning",
                "manual_confirmation_invalid",
                "manual_confirmation_text does not match the required confirmation text",
            )
            return "missing_or_invalid"
        return "confirmed"

    # -- summaries ------------------------------------------------------------

    def _prerequisite_summary(
        self,
        run: DetectionTrainingRun,
        readiness_report: Optional[DetectionTrainingReadinessReport],
        environment_spec: Optional[DetectionTrainingEnvironmentSpec],
    ) -> dict[str, Any]:
        return {
            "detection_training_run_status": run.status.value,
            "detection_training_run_is_runnable": run.is_runnable,
            "readiness_report_decision": readiness_report.decision.value if readiness_report else None,
            "readiness_report_status": readiness_report.status.value if readiness_report else None,
            "environment_spec_decision": environment_spec.decision.value if environment_spec else None,
            "environment_spec_status": environment_spec.status.value if environment_spec else None,
        }

    def _repository_safety_summary(self, report: RepositorySafetyReport) -> dict[str, Any]:
        return report.to_dict()

    def _risk_summary(self, issues: list[DetectionTrainingExecutionIssue]) -> dict[str, Any]:
        return {
            "error_codes": sorted({issue.code for issue in issues if issue.severity.value == "error"}),
            "warning_codes": sorted({issue.code for issue in issues if issue.severity.value == "warning"}),
        }

    def _recommendation_summary(
        self, error_codes: set[str], confirmation_status: str, status: DetectionTrainingExecutionStatus
    ) -> dict[str, Any]:
        recommendations: list[str] = []
        if error_codes & _PREREQUISITE_CODES:
            recommendations.append("fix the detection training run plan before requesting an execution gate")
        if error_codes & _READINESS_CODES:
            recommendations.append("resolve DetectionTrainingReadinessReport issues first")
        if error_codes & _ENVIRONMENT_CODES:
            recommendations.append("resolve DetectionTrainingEnvironmentSpec issues first")
        if error_codes & _ARTIFACT_POLICY_CODES:
            recommendations.append("resolve DetectionTrainingArtifactPolicy issues first")
        if error_codes & _REPOSITORY_SAFETY_CODES:
            recommendations.append("fix .gitignore coverage or move artifact_root_dir outside the repository")
        if error_codes & _CI_CODES:
            recommendations.append("never trigger real training from a CI job")
        if confirmation_status == "missing_or_invalid":
            recommendations.append("provide the exact required_confirmation_text to proceed past manual_required")
        if status == DetectionTrainingExecutionStatus.MANUAL_REQUIRED and not error_codes:
            recommendations.append("this run still requires a human to manually trigger training out-of-band")
        return {"next_steps": recommendations}

    @staticmethod
    def _decision(
        error_codes: set[str], status: DetectionTrainingExecutionStatus
    ) -> DetectionTrainingExecutionDecision:
        if error_codes & _PREREQUISITE_CODES:
            return DetectionTrainingExecutionDecision.BLOCKED_BY_PREREQUISITES
        if error_codes & _READINESS_CODES:
            return DetectionTrainingExecutionDecision.BLOCKED_BY_READINESS
        if error_codes & _ENVIRONMENT_CODES:
            return DetectionTrainingExecutionDecision.BLOCKED_BY_ENVIRONMENT
        if error_codes & _ARTIFACT_POLICY_CODES:
            return DetectionTrainingExecutionDecision.BLOCKED_BY_ARTIFACT_POLICY
        if error_codes & _REPOSITORY_SAFETY_CODES:
            return DetectionTrainingExecutionDecision.BLOCKED_BY_REPOSITORY_SAFETY
        if error_codes & _CI_CODES:
            return DetectionTrainingExecutionDecision.BLOCKED_BY_CI
        if error_codes & _CONFIGURATION_CODES:
            return DetectionTrainingExecutionDecision.BLOCKED_BY_CONFIGURATION
        if status == DetectionTrainingExecutionStatus.READY_TO_EXECUTE:
            return DetectionTrainingExecutionDecision.READY_FOR_MANUAL_EXECUTION
        return DetectionTrainingExecutionDecision.MANUAL_CONFIRMATION_REQUIRED

    @staticmethod
    def _issue(
        issues: list[DetectionTrainingExecutionIssue],
        severity: str,
        code: str,
        message: str,
        *,
        details: Optional[dict] = None,
    ) -> None:
        issues.append(
            DetectionTrainingExecutionIssue(
                execution_run_id=_PLACEHOLDER_RUN_ID,
                severity=DetectionTrainingExecutionIssueSeverity(severity),
                code=code,
                message=message,
                details=details,
            )
        )
