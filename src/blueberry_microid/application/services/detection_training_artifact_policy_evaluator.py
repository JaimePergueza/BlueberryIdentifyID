from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from blueberry_microid.domain.entities.annotation_bundle_file import AnnotationBundleFile
from blueberry_microid.domain.entities.annotation_bundle_run import AnnotationBundleRun
from blueberry_microid.domain.entities.detection_training_artifact_issue import DetectionTrainingArtifactIssue
from blueberry_microid.domain.entities.detection_training_artifact_record import DetectionTrainingArtifactRecord
from blueberry_microid.domain.entities.detection_training_environment_spec import DetectionTrainingEnvironmentSpec
from blueberry_microid.domain.entities.detection_training_run import DetectionTrainingRun
from blueberry_microid.domain.enums.detection_training_artifact_issue_severity import (
    DetectionTrainingArtifactIssueSeverity,
)
from blueberry_microid.domain.enums.detection_training_artifact_kind import DetectionTrainingArtifactKind
from blueberry_microid.domain.enums.detection_training_artifact_location_type import (
    DetectionTrainingArtifactLocationType,
)
from blueberry_microid.domain.enums.detection_training_artifact_policy_decision import (
    DetectionTrainingArtifactPolicyDecision,
)
from blueberry_microid.domain.enums.detection_training_artifact_policy_status import (
    DetectionTrainingArtifactPolicyStatus,
)
from blueberry_microid.domain.enums.detection_training_artifact_state import DetectionTrainingArtifactState
from blueberry_microid.domain.enums.detection_training_environment_decision import (
    DetectionTrainingEnvironmentDecision,
)
from blueberry_microid.domain.enums.detection_training_environment_status import DetectionTrainingEnvironmentStatus
from blueberry_microid.ml.configs.detection_training_artifact_policy_config import (
    DetectionTrainingArtifactPolicyConfig,
)

_PLACEHOLDER_POLICY_ID = UUID("00000000-0000-0000-0000-000000000000")

_ENVIRONMENT_CODES = {"environment_not_ready"}
_MISSING_OUTPUT_DIR_CODES = {"output_dir_missing"}
_REPO_STORAGE_CODES = {"output_dir_inside_repo"}
_FORBIDDEN_EXTENSION_CODES = {"artifact_extension_forbidden", "model_weight_in_repo_not_allowed"}
_POLICY_VIOLATION_CODES = {
    "actual_artifact_registration_not_allowed_yet",
    "checksum_missing_for_actual_artifact",
    "checksum_algorithm_not_allowed",
    "artifact_size_exceeds_policy",
    "gitignore_missing",
    "gitignore_does_not_exclude_weights",
}

_ACCEPTABLE_ENVIRONMENT_DECISIONS = {
    DetectionTrainingEnvironmentDecision.ENVIRONMENT_READY,
    DetectionTrainingEnvironmentDecision.NEEDS_MANUAL_SETUP,
}

_OUTPUT_KEY_TO_KIND = {
    "weights_path_planned": DetectionTrainingArtifactKind.PLANNED_WEIGHTS,
    "metrics_path_planned": DetectionTrainingArtifactKind.PLANNED_METRICS,
    "predictions_path_planned": DetectionTrainingArtifactKind.PLANNED_PREDICTIONS,
    "run_dir_planned": DetectionTrainingArtifactKind.PLANNED_RUN_DIR,
}


@dataclass(frozen=True)
class DetectionTrainingArtifactPolicyEvaluation:
    decision: DetectionTrainingArtifactPolicyDecision
    status: DetectionTrainingArtifactPolicyStatus
    is_policy_ready: bool
    planned_output_summary: dict[str, Any]
    storage_policy: dict[str, Any]
    git_policy: dict[str, Any]
    checksum_policy: dict[str, Any]
    registry_summary: dict[str, Any]
    risk_summary: dict[str, Any]
    recommendation_summary: dict[str, Any]
    artifact_records: list[DetectionTrainingArtifactRecord] = field(default_factory=list)
    issues: list[DetectionTrainingArtifactIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[DetectionTrainingArtifactIssue]:
        return [issue for issue in self.issues if issue.severity == DetectionTrainingArtifactIssueSeverity.ERROR]

    @property
    def warnings(self) -> list[DetectionTrainingArtifactIssue]:
        return [issue for issue in self.issues if issue.severity == DetectionTrainingArtifactIssueSeverity.WARNING]

    @property
    def infos(self) -> list[DetectionTrainingArtifactIssue]:
        return [issue for issue in self.issues if issue.severity == DetectionTrainingArtifactIssueSeverity.INFO]


class DetectionTrainingArtifactPolicyEvaluator:
    """Specifies/validates where a future real training attempt's artifacts
    (weights, metrics, predictions, logs) would be stored.

    Purely an inspection of already-persisted metadata plus safe, read-only
    filesystem checks (`pathlib` existence/location, reading `.gitignore`
    text). Never writes artifact files, never creates directories, never
    modifies `.gitignore`, never computes checksums of real files, and never
    trains anything.
    """

    def evaluate(
        self,
        detection_training_run: DetectionTrainingRun,
        environment_spec: DetectionTrainingEnvironmentSpec,
        bundle_run: Optional[AnnotationBundleRun],
        bundle_files: list[AnnotationBundleFile],
        config: DetectionTrainingArtifactPolicyConfig,
    ) -> DetectionTrainingArtifactPolicyEvaluation:
        issues: list[DetectionTrainingArtifactIssue] = []
        records: list[DetectionTrainingArtifactRecord] = []

        self._evaluate_environment(environment_spec, config, issues)

        artifact_root_inside_repo = self._evaluate_artifact_root(config, issues)
        planned_output_summary = self._evaluate_expected_outputs(
            detection_training_run, config, issues, records
        )
        self._evaluate_git_policy_issues(config, issues)
        self._evaluate_registry_policy(config, issues)

        self._issue(issues, "info", "no_training_executed", "no training was executed by this evaluation")
        if any(record.artifact_kind == DetectionTrainingArtifactKind.PLANNED_WEIGHTS for record in records):
            self._issue(
                issues,
                "info",
                "planned_artifact_only",
                "planned_weights is a description of a future path only; no weight file exists yet",
            )

        status = self._status(issues)
        decision = self._decision(issues, status)
        is_policy_ready = (
            status in {DetectionTrainingArtifactPolicyStatus.READY, DetectionTrainingArtifactPolicyStatus.WARNING}
            and decision == DetectionTrainingArtifactPolicyDecision.ARTIFACT_POLICY_READY
        )

        storage_policy = self._storage_policy(config, artifact_root_inside_repo)
        git_policy = self._git_policy(config)
        checksum_policy = self._checksum_policy(config)
        registry_summary = self._registry_summary(records)
        risk_summary = self._risk_summary(issues)
        recommendation_summary = self._recommendation_summary(issues)

        return DetectionTrainingArtifactPolicyEvaluation(
            decision=decision,
            status=status,
            is_policy_ready=is_policy_ready,
            planned_output_summary=planned_output_summary,
            storage_policy=storage_policy,
            git_policy=git_policy,
            checksum_policy=checksum_policy,
            registry_summary=registry_summary,
            risk_summary=risk_summary,
            recommendation_summary=recommendation_summary,
            artifact_records=records,
            issues=issues,
        )

    # -- A. upstream (environment) ---------------------------------------

    def _evaluate_environment(
        self,
        environment_spec: DetectionTrainingEnvironmentSpec,
        config: DetectionTrainingArtifactPolicyConfig,
        issues: list[DetectionTrainingArtifactIssue],
    ) -> None:
        if environment_spec.status in {
            DetectionTrainingEnvironmentStatus.BLOCKED,
            DetectionTrainingEnvironmentStatus.FAILED,
        }:
            self._issue(
                issues,
                "error",
                "environment_not_ready",
                f"environment spec status is '{environment_spec.status.value}'; the artifact policy cannot be ready",
            )
        elif environment_spec.decision not in _ACCEPTABLE_ENVIRONMENT_DECISIONS:
            self._issue(
                issues,
                "error" if config.strict_mode else "warning",
                "environment_not_ready",
                f"environment spec decision is '{environment_spec.decision.value}', not 'environment_ready' or "
                "'needs_manual_setup'",
            )

    # -- C. paths ----------------------------------------------------------

    def _evaluate_artifact_root(
        self,
        config: DetectionTrainingArtifactPolicyConfig,
        issues: list[DetectionTrainingArtifactIssue],
    ) -> Optional[bool]:
        if not config.artifact_root_dir:
            if config.require_artifact_root_dir:
                self._issue(
                    issues,
                    "error",
                    "output_dir_missing",
                    "artifact_root_dir is not configured; a ready artifact policy needs a declared root directory",
                )
            return None

        path = Path(config.artifact_root_dir)
        inside_repo = self._is_inside_repo(path)
        if inside_repo and not config.allow_artifacts_inside_repo:
            self._issue(
                issues,
                "error",
                "output_dir_inside_repo",
                "artifact_root_dir resolves inside the repository but allow_artifacts_inside_repo=false",
                artifact_path=config.artifact_root_dir,
            )
        if not path.is_absolute():
            self._issue(
                issues,
                "error" if config.strict_mode else "warning",
                "output_dir_not_absolute",
                "artifact_root_dir is not an absolute path",
                artifact_path=config.artifact_root_dir,
            )
        return inside_repo

    # -- B/D. expected_outputs + extensions ---------------------------------

    def _evaluate_expected_outputs(
        self,
        run: DetectionTrainingRun,
        config: DetectionTrainingArtifactPolicyConfig,
        issues: list[DetectionTrainingArtifactIssue],
        records: list[DetectionTrainingArtifactRecord],
    ) -> dict[str, Any]:
        expected_outputs = run.expected_outputs or {}
        summary: dict[str, Any] = {}
        for output_key, kind in _OUTPUT_KEY_TO_KIND.items():
            raw_path = expected_outputs.get(output_key)
            summary[output_key] = raw_path
            if not raw_path:
                if not config.allow_missing_planned_paths:
                    self._issue(
                        issues,
                        "warning",
                        "artifact_path_missing",
                        f"expected_outputs is missing '{output_key}'",
                    )
                continue

            location_type, inside_repo = self._classify_path(raw_path)
            extension = Path(raw_path).suffix.lower() if location_type != "external_uri" else None

            if location_type == "local_path" and inside_repo and extension in config.forbidden_extensions:
                code = (
                    "model_weight_in_repo_not_allowed"
                    if kind == DetectionTrainingArtifactKind.PLANNED_WEIGHTS
                    else "artifact_extension_forbidden"
                )
                self._issue(
                    issues,
                    "error",
                    code,
                    f"'{output_key}' points inside the repository with forbidden extension '{extension}'",
                    artifact_path=raw_path,
                )
                state = DetectionTrainingArtifactState.FORBIDDEN
            elif location_type == "external_uri" and not config.allow_external_uri:
                self._issue(
                    issues,
                    "warning",
                    "external_storage_not_configured",
                    f"'{output_key}' resolves to an external URI but allow_external_uri=false",
                    artifact_path=raw_path,
                )
                state = DetectionTrainingArtifactState.PLANNED
            else:
                state = DetectionTrainingArtifactState.PLANNED

            if config.register_planned_artifacts:
                records.append(
                    DetectionTrainingArtifactRecord(
                        artifact_policy_id=_PLACEHOLDER_POLICY_ID,
                        detection_training_run_id=run.id,
                        artifact_kind=kind,
                        artifact_state=state,
                        location_type=DetectionTrainingArtifactLocationType(location_type),
                        artifact_path=raw_path if location_type != "external_uri" else None,
                        external_uri=raw_path if location_type == "external_uri" else None,
                        file_extension=extension,
                        metadata={"source": "expected_outputs", "output_key": output_key},
                    )
                )
        return summary

    # -- E. git policy ----------------------------------------------------

    def _evaluate_git_policy_issues(
        self,
        config: DetectionTrainingArtifactPolicyConfig,
        issues: list[DetectionTrainingArtifactIssue],
    ) -> None:
        if not config.require_gitignore_rules:
            return
        gitignore_path = self._repo_root() / ".gitignore" if self._repo_root() is not None else None
        if gitignore_path is None or not gitignore_path.exists():
            self._issue(
                issues,
                "error" if config.strict_mode else "warning",
                "gitignore_missing",
                "no .gitignore file was found at the repository root",
            )
            return
        try:
            content = gitignore_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            content = ""
        lines = {line.strip() for line in content.splitlines()}
        missing_patterns = [pattern for pattern in config.required_gitignore_patterns if pattern not in lines]
        if missing_patterns:
            self._issue(
                issues,
                "error" if config.strict_mode else "warning",
                "gitignore_does_not_exclude_weights",
                f".gitignore is missing recommended patterns: {', '.join(missing_patterns)}",
                details={"missing_patterns": missing_patterns},
            )

    # -- G. registry (actual-artifact policy) ------------------------------

    def _evaluate_registry_policy(
        self,
        config: DetectionTrainingArtifactPolicyConfig,
        issues: list[DetectionTrainingArtifactIssue],
    ) -> None:
        if config.register_actual_artifacts and not config.allow_actual_artifact_registration:
            self._issue(
                issues,
                "error",
                "actual_artifact_registration_not_allowed_yet",
                "register_actual_artifacts=true but allow_actual_artifact_registration=false: actual artifacts "
                "are always blocked in this phase",
            )

    # -- summaries ----------------------------------------------------------

    def _storage_policy(
        self, config: DetectionTrainingArtifactPolicyConfig, artifact_root_inside_repo: Optional[bool]
    ) -> dict[str, Any]:
        return {
            "artifact_root_dir": config.artifact_root_dir,
            "artifact_root_dir_inside_repo": artifact_root_inside_repo,
            "allow_artifacts_inside_repo": config.allow_artifacts_inside_repo,
            "allow_artifacts_outside_repo": config.allow_artifacts_outside_repo,
            "allow_external_uri": config.allow_external_uri,
            "allowed_external_uri_schemes": list(config.allowed_external_uri_schemes),
            "forbidden_extensions": list(config.forbidden_extensions),
            "allowed_metadata_extensions": list(config.allowed_metadata_extensions),
            "max_artifact_size_mb": config.max_artifact_size_mb,
        }

    def _git_policy(self, config: DetectionTrainingArtifactPolicyConfig) -> dict[str, Any]:
        return {
            "require_gitignore_rules": config.require_gitignore_rules,
            "required_gitignore_patterns": list(config.required_gitignore_patterns),
            "gitignore_modified": False,
        }

    def _checksum_policy(self, config: DetectionTrainingArtifactPolicyConfig) -> dict[str, Any]:
        return {
            "require_checksums_for_actual_artifacts": config.require_checksums_for_actual_artifacts,
            "checksum_algorithm": config.checksum_algorithm,
            "checksums_computed": False,
        }

    def _registry_summary(self, records: list[DetectionTrainingArtifactRecord]) -> dict[str, Any]:
        return {
            "planned_record_count": len(records),
            "actual_record_count": 0,
            "recorded_kinds": sorted({record.artifact_kind.value for record in records}),
        }

    def _risk_summary(self, issues: list[DetectionTrainingArtifactIssue]) -> dict[str, Any]:
        return {
            "error_codes": sorted({issue.code for issue in issues if issue.severity.value == "error"}),
            "warning_codes": sorted({issue.code for issue in issues if issue.severity.value == "warning"}),
        }

    def _recommendation_summary(self, issues: list[DetectionTrainingArtifactIssue]) -> dict[str, Any]:
        codes = {issue.code for issue in issues}
        recommendations: list[str] = []
        if "environment_not_ready" in codes:
            recommendations.append("resolve DetectionTrainingEnvironmentSpec issues before specifying artifacts")
        if "output_dir_missing" in codes:
            recommendations.append("declare an artifact_root_dir outside the repository")
        if "output_dir_inside_repo" in codes:
            recommendations.append("move artifact_root_dir outside the repository")
        if codes & _FORBIDDEN_EXTENSION_CODES:
            recommendations.append("store weight/model files outside the repository, never inside it")
        if "gitignore_missing" in codes or "gitignore_does_not_exclude_weights" in codes:
            recommendations.append("add the recommended .gitignore patterns manually before real training")
        return {"next_steps": recommendations}

    @staticmethod
    def _status(issues: list[DetectionTrainingArtifactIssue]) -> DetectionTrainingArtifactPolicyStatus:
        if any(issue.severity == DetectionTrainingArtifactIssueSeverity.ERROR for issue in issues):
            return DetectionTrainingArtifactPolicyStatus.BLOCKED
        if any(issue.severity == DetectionTrainingArtifactIssueSeverity.WARNING for issue in issues):
            return DetectionTrainingArtifactPolicyStatus.WARNING
        return DetectionTrainingArtifactPolicyStatus.READY

    @staticmethod
    def _decision(
        issues: list[DetectionTrainingArtifactIssue], status: DetectionTrainingArtifactPolicyStatus
    ) -> DetectionTrainingArtifactPolicyDecision:
        error_codes = {
            issue.code for issue in issues if issue.severity == DetectionTrainingArtifactIssueSeverity.ERROR
        }
        if error_codes & _ENVIRONMENT_CODES:
            return DetectionTrainingArtifactPolicyDecision.BLOCKED_BY_ENVIRONMENT
        if error_codes & _MISSING_OUTPUT_DIR_CODES:
            return DetectionTrainingArtifactPolicyDecision.BLOCKED_BY_MISSING_OUTPUT_DIR
        if error_codes & _REPO_STORAGE_CODES:
            return DetectionTrainingArtifactPolicyDecision.BLOCKED_BY_REPO_STORAGE
        if error_codes & _FORBIDDEN_EXTENSION_CODES:
            return DetectionTrainingArtifactPolicyDecision.BLOCKED_BY_FORBIDDEN_EXTENSION
        if error_codes & _POLICY_VIOLATION_CODES:
            return DetectionTrainingArtifactPolicyDecision.BLOCKED_BY_POLICY_VIOLATION
        if status == DetectionTrainingArtifactPolicyStatus.WARNING:
            return DetectionTrainingArtifactPolicyDecision.NEEDS_EXTERNAL_STORAGE
        return DetectionTrainingArtifactPolicyDecision.ARTIFACT_POLICY_READY

    @staticmethod
    def _classify_path(raw_path: str) -> tuple[str, Optional[bool]]:
        if "://" in raw_path:
            return "external_uri", None
        path = Path(raw_path)
        if not path.is_absolute():
            return "relative_path", None
        return "local_path", DetectionTrainingArtifactPolicyEvaluator._is_inside_repo(path)

    @staticmethod
    def _repo_root() -> Optional[Path]:
        try:
            return Path(__file__).resolve().parents[4]
        except IndexError:
            return None

    @staticmethod
    def _is_inside_repo(path: Path) -> Optional[bool]:
        repo_root = DetectionTrainingArtifactPolicyEvaluator._repo_root()
        if repo_root is None:
            return None
        try:
            resolved = path.resolve()
        except OSError:
            return None
        try:
            resolved.relative_to(repo_root)
            return True
        except ValueError:
            return False

    @staticmethod
    def _issue(
        issues: list[DetectionTrainingArtifactIssue],
        severity: str,
        code: str,
        message: str,
        *,
        artifact_path: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> None:
        issues.append(
            DetectionTrainingArtifactIssue(
                artifact_policy_id=_PLACEHOLDER_POLICY_ID,
                severity=DetectionTrainingArtifactIssueSeverity(severity),
                code=code,
                message=message,
                artifact_path=artifact_path,
                details=details,
            )
        )
