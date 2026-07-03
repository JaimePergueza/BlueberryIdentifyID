from __future__ import annotations

import importlib.util
import os
import platform
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from blueberry_microid.domain.entities.annotation_bundle_file import AnnotationBundleFile
from blueberry_microid.domain.entities.annotation_bundle_run import AnnotationBundleRun
from blueberry_microid.domain.entities.detection_training_environment_issue import (
    DetectionTrainingEnvironmentIssue,
)
from blueberry_microid.domain.entities.detection_training_readiness_issue import DetectionTrainingReadinessIssue
from blueberry_microid.domain.entities.detection_training_readiness_report import DetectionTrainingReadinessReport
from blueberry_microid.domain.entities.detection_training_run import DetectionTrainingRun
from blueberry_microid.domain.enums.detection_training_environment_decision import (
    DetectionTrainingEnvironmentDecision,
)
from blueberry_microid.domain.enums.detection_training_environment_issue_severity import (
    DetectionTrainingEnvironmentIssueSeverity,
)
from blueberry_microid.domain.enums.detection_training_environment_status import DetectionTrainingEnvironmentStatus
from blueberry_microid.domain.enums.detection_training_readiness_decision import DetectionTrainingReadinessDecision
from blueberry_microid.domain.enums.detection_training_readiness_status import DetectionTrainingReadinessStatus
from blueberry_microid.ml.configs.detection_training_environment_config import DetectionTrainingEnvironmentConfig

_PLACEHOLDER_SPEC_ID = UUID("00000000-0000-0000-0000-000000000000")
_FORBIDDEN_TERMS = ("bacteria", "fungi", "fungus", "colony", "species", "genus", "taxon", "diagnosis")
_ALLOWED_CATEGORY = "candidate_region"
_CI_ENV_VARS = ("CI", "GITHUB_ACTIONS")

_READINESS_CODES = {"readiness_not_ready"}
_UNSUPPORTED_PLATFORM_CODES = {"python_version_mismatch", "unsupported_os"}
_MISSING_REQUIREMENTS_CODES = {
    "ultralytics_not_installed",
    "torch_not_installed",
    "gpu_not_available",
    "cuda_not_available",
}
_POLICY_CODES = {
    "external_weights_not_allowed",
    "ci_training_not_allowed",
    "taxonomy_not_allowed",
    "weights_policy_missing",
}
_STORAGE_POLICY_CODES = {"output_dir_not_specified", "output_dir_not_writable", "artifact_storage_policy_missing"}
_DEPENDENCY_POLICY_CODES = {"dependency_installation_not_allowed", "artifacts_inside_repo_policy_risk"}


@dataclass(frozen=True)
class DetectionTrainingEnvironmentEvaluation:
    decision: DetectionTrainingEnvironmentDecision
    status: DetectionTrainingEnvironmentStatus
    is_environment_ready: bool
    detected_environment: dict[str, Any]
    dependency_policy: dict[str, Any]
    hardware_policy: dict[str, Any]
    artifact_policy: dict[str, Any]
    execution_policy: dict[str, Any]
    setup_instructions: dict[str, Any]
    safe_check_summary: dict[str, Any]
    risk_summary: dict[str, Any]
    recommendation_summary: dict[str, Any]
    issues: list[DetectionTrainingEnvironmentIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[DetectionTrainingEnvironmentIssue]:
        return [issue for issue in self.issues if issue.severity == DetectionTrainingEnvironmentIssueSeverity.ERROR]

    @property
    def warnings(self) -> list[DetectionTrainingEnvironmentIssue]:
        return [
            issue for issue in self.issues if issue.severity == DetectionTrainingEnvironmentIssueSeverity.WARNING
        ]

    @property
    def infos(self) -> list[DetectionTrainingEnvironmentIssue]:
        return [issue for issue in self.issues if issue.severity == DetectionTrainingEnvironmentIssueSeverity.INFO]


class DetectionTrainingEnvironmentEvaluator:
    """Specifies/validates the environment a future real training attempt
    would run in, purely from already-persisted metadata and safe,
    non-invasive checks (`sys.version_info`, `platform.system()`,
    `importlib.util.find_spec`, `pathlib` existence checks).

    Never imports `ultralytics`/`torch`, never calls `subprocess`, never
    queries a GPU/CUDA driver, never installs or downloads anything, and
    never writes real files. `is_environment_ready=true` never means a real
    training environment was provisioned or that training was executed.
    """

    def evaluate(
        self,
        detection_training_run: DetectionTrainingRun,
        readiness_report: DetectionTrainingReadinessReport,
        readiness_issues: list[DetectionTrainingReadinessIssue],
        bundle_run: Optional[AnnotationBundleRun],
        bundle_files: list[AnnotationBundleFile],
        config: DetectionTrainingEnvironmentConfig,
    ) -> DetectionTrainingEnvironmentEvaluation:
        issues: list[DetectionTrainingEnvironmentIssue] = []

        self._evaluate_readiness(readiness_report, issues)
        detected_environment = self._evaluate_python_and_platform(config, issues)
        dependency_policy = self._evaluate_dependencies(config, issues)
        hardware_policy = self._evaluate_hardware(config, issues)
        artifact_policy = self._evaluate_artifacts(config, issues)
        execution_policy = self._evaluate_execution(config, issues)
        self._evaluate_categories(bundle_run, issues)

        self._issue(issues, "info", "no_training_executed", "no training was executed by this evaluation")
        self._issue(
            issues,
            "info",
            "environment_check_safe_only",
            "only safe, non-invasive checks were performed: no subprocess, no GPU/CUDA queries, "
            "no ultralytics/torch import, no installation",
        )

        status = self._status(issues)
        decision = self._decision(issues, readiness_report, status)
        is_environment_ready = (
            status in {DetectionTrainingEnvironmentStatus.READY, DetectionTrainingEnvironmentStatus.WARNING}
            and decision == DetectionTrainingEnvironmentDecision.ENVIRONMENT_READY
        )

        setup_instructions = self._setup_instructions(config)
        safe_check_summary = self._safe_check_summary(detected_environment)
        risk_summary = self._risk_summary(issues)
        recommendation_summary = self._recommendation_summary(issues)

        return DetectionTrainingEnvironmentEvaluation(
            decision=decision,
            status=status,
            is_environment_ready=is_environment_ready,
            detected_environment=detected_environment,
            dependency_policy=dependency_policy,
            hardware_policy=hardware_policy,
            artifact_policy=artifact_policy,
            execution_policy=execution_policy,
            setup_instructions=setup_instructions,
            safe_check_summary=safe_check_summary,
            risk_summary=risk_summary,
            recommendation_summary=recommendation_summary,
            issues=issues,
        )

    # -- A. readiness precondition ---------------------------------------

    def _evaluate_readiness(
        self,
        readiness_report: DetectionTrainingReadinessReport,
        issues: list[DetectionTrainingEnvironmentIssue],
    ) -> None:
        if readiness_report.status in {
            DetectionTrainingReadinessStatus.BLOCKED,
            DetectionTrainingReadinessStatus.FAILED,
        }:
            self._issue(
                issues,
                "error",
                "readiness_not_ready",
                f"readiness report status is '{readiness_report.status.value}'; the environment cannot be ready",
            )
        elif readiness_report.decision != DetectionTrainingReadinessDecision.READY_FOR_TRAINING:
            self._issue(
                issues,
                "error",
                "readiness_not_ready",
                f"readiness report decision is '{readiness_report.decision.value}', not 'ready_for_training'",
            )

    # -- B. python and platform -------------------------------------------

    def _evaluate_python_and_platform(
        self,
        config: DetectionTrainingEnvironmentConfig,
        issues: list[DetectionTrainingEnvironmentIssue],
    ) -> dict[str, Any]:
        version_info = sys.version_info
        detected_python_version = f"{version_info.major}.{version_info.minor}.{version_info.micro}"
        detected_os = platform.system()

        python_version_matches: Optional[bool] = None
        if config.target_python_version:
            python_version_matches = detected_python_version.startswith(config.target_python_version)
            if not python_version_matches:
                self._issue(
                    issues,
                    "error",
                    "python_version_mismatch",
                    f"detected Python {detected_python_version} does not match target "
                    f"{config.target_python_version}",
                )
        else:
            self._issue(
                issues, "info", "python_version_not_specified", "no target_python_version was configured"
            )

        os_matches: Optional[bool] = None
        if config.target_os:
            os_matches = detected_os.lower() == config.target_os.lower()
            if not os_matches:
                self._issue(
                    issues,
                    "error",
                    "unsupported_os",
                    f"detected OS '{detected_os}' does not match target '{config.target_os}'",
                )
        else:
            self._issue(issues, "info", "os_not_specified", "no target_os was configured")

        return {
            "detected_python_version": detected_python_version,
            "target_python_version": config.target_python_version,
            "python_version_matches": python_version_matches,
            "detected_os": detected_os,
            "target_os": config.target_os,
            "os_matches": os_matches,
        }

    # -- C. dependencies ----------------------------------------------------

    def _evaluate_dependencies(
        self,
        config: DetectionTrainingEnvironmentConfig,
        issues: list[DetectionTrainingEnvironmentIssue],
    ) -> dict[str, Any]:
        if not config.target_ultralytics_version and config.require_ultralytics:
            self._issue(
                issues,
                "info",
                "ultralytics_version_not_specified",
                "require_ultralytics=true but no target_ultralytics_version was configured",
            )
        if not config.target_torch_version and config.require_torch:
            self._issue(
                issues,
                "info",
                "torch_version_not_specified",
                "require_torch=true but no target_torch_version was configured",
            )

        ultralytics_available = self._find_spec_safely("ultralytics") if config.require_ultralytics else None
        torch_available = self._find_spec_safely("torch") if config.require_torch else None

        if config.require_ultralytics and not ultralytics_available:
            self._issue(
                issues,
                "error",
                "ultralytics_not_installed",
                "require_ultralytics=true but ultralytics is not available in this environment "
                "(checked only via importlib.util.find_spec, never imported)",
            )
        if config.require_torch and not torch_available:
            self._issue(
                issues,
                "error",
                "torch_not_installed",
                "require_torch=true but torch is not available in this environment "
                "(checked only via importlib.util.find_spec, never imported)",
            )
        if not config.allow_dependency_installation:
            self._issue(
                issues,
                "info",
                "dependency_installation_not_allowed",
                "allow_dependency_installation=false: any missing dependency must be installed manually",
            )

        return {
            "require_ultralytics": config.require_ultralytics,
            "target_ultralytics_version": config.target_ultralytics_version,
            "ultralytics_available": ultralytics_available,
            "require_torch": config.require_torch,
            "target_torch_version": config.target_torch_version,
            "torch_available": torch_available,
            "allow_dependency_installation": config.allow_dependency_installation,
        }

    # -- D. hardware --------------------------------------------------------

    def _evaluate_hardware(
        self,
        config: DetectionTrainingEnvironmentConfig,
        issues: list[DetectionTrainingEnvironmentIssue],
    ) -> dict[str, Any]:
        if config.allow_cpu_training:
            self._issue(
                issues,
                "warning",
                "manual_training_required",
                "allow_cpu_training=true: CPU training is permitted for a future attempt but may be slow",
            )
        if not config.require_gpu and not config.require_cuda:
            pass
        if config.require_gpu:
            self._issue(
                issues,
                "error",
                "gpu_not_available",
                "require_gpu=true but this evaluator never queries GPU availability via torch.cuda, "
                "nvidia-smi, or drivers — there is no safe way to confirm it",
            )
        if config.require_cuda:
            self._issue(
                issues,
                "error",
                "cuda_not_available",
                "require_cuda=true but this evaluator never queries CUDA availability via external commands",
            )
            if not config.target_cuda_version:
                self._issue(
                    issues, "info", "cuda_policy_not_specified", "require_cuda=true but no target_cuda_version"
                )

        return {
            "allow_cpu_training": config.allow_cpu_training,
            "require_gpu": config.require_gpu,
            "require_cuda": config.require_cuda,
            "target_cuda_version": config.target_cuda_version,
            "gpu_available_verified": False,
            "cuda_available_verified": False,
        }

    # -- E. weights + F. artifacts --------------------------------------------

    def _evaluate_artifacts(
        self,
        config: DetectionTrainingEnvironmentConfig,
        issues: list[DetectionTrainingEnvironmentIssue],
    ) -> dict[str, Any]:
        if config.pretrained_weights_path and not config.allow_external_weights:
            self._issue(
                issues,
                "error",
                "external_weights_not_allowed",
                "pretrained_weights_path is set but allow_external_weights=false; no weights are downloaded",
            )
        elif config.allow_external_weights:
            self._issue(
                issues,
                "info",
                "external_weights_policy_declared",
                "allow_external_weights=true: only the policy is recorded, nothing is downloaded",
            )
        if config.pretrained_weights_policy == "none":
            self._issue(
                issues,
                "error" if config.strict_mode else "warning",
                "weights_policy_missing",
                "pretrained_weights_policy is 'none': no base-weights policy has been decided yet",
            )

        output_dir_inside_repo: Optional[bool] = None
        output_dir_exists: Optional[bool] = None
        if not config.artifact_output_dir:
            self._issue(
                issues,
                "error" if config.strict_mode else "warning",
                "output_dir_not_specified",
                "artifact_output_dir is not configured; a ready environment needs a declared output location",
            )
        else:
            path = Path(config.artifact_output_dir)
            output_dir_exists = path.exists()
            output_dir_inside_repo = self._is_inside_repo(path)
            if not output_dir_exists:
                self._issue(
                    issues,
                    "warning",
                    "output_dir_not_writable",
                    "artifact_output_dir does not exist yet; it must be created manually before real training "
                    "(never created automatically by this evaluator)",
                )
            if output_dir_inside_repo and not config.allow_artifacts_inside_repo:
                self._issue(
                    issues,
                    "error",
                    "artifact_storage_policy_missing",
                    "artifact_output_dir resolves inside the repository but allow_artifacts_inside_repo=false",
                )

        if config.allow_artifacts_inside_repo:
            self._issue(
                issues,
                "error" if config.strict_mode else "warning",
                "artifacts_inside_repo_policy_risk",
                "allow_artifacts_inside_repo=true: storing training artifacts inside the repository is risky "
                "(large binaries, weights, or outputs could get committed)",
            )

        return {
            "artifact_output_dir": config.artifact_output_dir,
            "output_dir_exists": output_dir_exists,
            "output_dir_inside_repo": output_dir_inside_repo,
            "allow_artifacts_outside_repo": config.allow_artifacts_outside_repo,
            "allow_artifacts_inside_repo": config.allow_artifacts_inside_repo,
            "max_expected_artifact_size_mb": config.max_expected_artifact_size_mb,
            "pretrained_weights_policy": config.pretrained_weights_policy,
            "allow_external_weights": config.allow_external_weights,
            "pretrained_weights_path": config.pretrained_weights_path,
            "write_check_performed": False,
        }

    # -- G. CI + execution policy ---------------------------------------------

    def _evaluate_execution(
        self,
        config: DetectionTrainingEnvironmentConfig,
        issues: list[DetectionTrainingEnvironmentIssue],
    ) -> dict[str, Any]:
        detected_ci = any(os.environ.get(var) for var in _CI_ENV_VARS)
        if config.allow_ci_training:
            self._issue(
                issues,
                "error",
                "ci_training_not_allowed",
                "allow_ci_training=true is not a permitted policy; CI must never run real training",
                details={"detected_ci": detected_ci, "allow_ci_training": config.allow_ci_training},
            )
        elif detected_ci:
            # Running this evaluation from inside a CI job does not by itself
            # mean a future real training step would run in CI — only
            # allow_ci_training=true is a hard policy violation. This is a
            # non-blocking heads-up so operators double-check the pipeline.
            self._issue(
                issues,
                "warning",
                "ci_training_not_allowed",
                "this evaluation is running inside a detected CI environment; ensure no real training step is "
                "ever added to this pipeline",
                details={"detected_ci": detected_ci, "allow_ci_training": config.allow_ci_training},
            )
        if config.require_manual_confirmation:
            self._issue(
                issues,
                "info",
                "manual_training_required",
                "require_manual_confirmation=true: a human must explicitly approve any future real training run",
            )

        return {
            "allow_ci_training": config.allow_ci_training,
            "allow_local_training": config.allow_local_training,
            "require_manual_confirmation": config.require_manual_confirmation,
            "detected_ci": detected_ci,
        }

    # -- H. taxonomy ----------------------------------------------------------

    def _evaluate_categories(
        self,
        bundle_run: Optional[AnnotationBundleRun],
        issues: list[DetectionTrainingEnvironmentIssue],
    ) -> None:
        if bundle_run is None:
            return
        categories = bundle_run.config.get("categories") if isinstance(bundle_run.config, dict) else None
        if not categories:
            return
        for category in categories:
            lowered = str(category).lower()
            if any(term in lowered for term in _FORBIDDEN_TERMS) or category != _ALLOWED_CATEGORY:
                self._issue(
                    issues, "error", "taxonomy_not_allowed", f"category not allowed for training: {category}"
                )

    # -- summaries --------------------------------------------------------

    def _setup_instructions(self, config: DetectionTrainingEnvironmentConfig) -> dict[str, Any]:
        commands: list[str] = []
        if config.require_ultralytics:
            version_suffix = f"=={config.target_ultralytics_version}" if config.target_ultralytics_version else ""
            commands.append(f"pip install ultralytics{version_suffix}  # not executed by this evaluator")
        if config.require_torch:
            version_suffix = f"=={config.target_torch_version}" if config.target_torch_version else ""
            commands.append(f"pip install torch{version_suffix}  # not executed by this evaluator")
        if config.artifact_output_dir:
            commands.append(f"mkdir -p {config.artifact_output_dir}  # not executed by this evaluator")
        return {"suggested_commands": commands, "commands_executed": False}

    def _safe_check_summary(self, detected_environment: dict[str, Any]) -> dict[str, Any]:
        return {
            "checks_performed": [
                "sys.version_info",
                "platform.system()",
                "importlib.util.find_spec (no import)",
                "pathlib existence/location checks (no writes by default)",
                "os.environ CI variable lookup",
            ],
            "checks_skipped": [
                "subprocess execution",
                "GPU/CUDA driver queries",
                "ultralytics/torch import",
                "dependency installation",
                "weight/dataset downloads",
            ],
            "detected_python_version": detected_environment["detected_python_version"],
            "detected_os": detected_environment["detected_os"],
        }

    def _risk_summary(self, issues: list[DetectionTrainingEnvironmentIssue]) -> dict[str, Any]:
        return {
            "error_codes": sorted({issue.code for issue in issues if issue.severity.value == "error"}),
            "warning_codes": sorted({issue.code for issue in issues if issue.severity.value == "warning"}),
        }

    def _recommendation_summary(self, issues: list[DetectionTrainingEnvironmentIssue]) -> dict[str, Any]:
        codes = {issue.code for issue in issues}
        recommendations: list[str] = []
        if "readiness_not_ready" in codes:
            recommendations.append("resolve DetectionTrainingReadinessReport issues before specifying environment")
        if codes & _UNSUPPORTED_PLATFORM_CODES:
            recommendations.append("align target_python_version/target_os with the actual training machine")
        if codes & _MISSING_REQUIREMENTS_CODES:
            recommendations.append("decide and document an ultralytics/torch/GPU/CUDA installation plan manually")
        if codes & _STORAGE_POLICY_CODES:
            recommendations.append("declare a writable artifact_output_dir outside the repository")
        if "ci_training_not_allowed" in codes:
            recommendations.append("never enable allow_ci_training; real training must stay a manual/local step")
        if "weights_policy_missing" in codes:
            recommendations.append("decide a pretrained_weights_policy before real training")
        return {"next_steps": recommendations}

    @staticmethod
    def _status(issues: list[DetectionTrainingEnvironmentIssue]) -> DetectionTrainingEnvironmentStatus:
        if any(issue.severity == DetectionTrainingEnvironmentIssueSeverity.ERROR for issue in issues):
            return DetectionTrainingEnvironmentStatus.BLOCKED
        if any(issue.severity == DetectionTrainingEnvironmentIssueSeverity.WARNING for issue in issues):
            return DetectionTrainingEnvironmentStatus.WARNING
        return DetectionTrainingEnvironmentStatus.READY

    @staticmethod
    def _decision(
        issues: list[DetectionTrainingEnvironmentIssue],
        readiness_report: DetectionTrainingReadinessReport,
        status: DetectionTrainingEnvironmentStatus,
    ) -> DetectionTrainingEnvironmentDecision:
        error_codes = {
            issue.code for issue in issues if issue.severity == DetectionTrainingEnvironmentIssueSeverity.ERROR
        }
        if error_codes & _READINESS_CODES:
            return DetectionTrainingEnvironmentDecision.BLOCKED_BY_MISSING_REQUIREMENTS
        if error_codes & _UNSUPPORTED_PLATFORM_CODES:
            return DetectionTrainingEnvironmentDecision.BLOCKED_BY_UNSUPPORTED_PLATFORM
        if error_codes & _MISSING_REQUIREMENTS_CODES:
            return DetectionTrainingEnvironmentDecision.BLOCKED_BY_MISSING_REQUIREMENTS
        if error_codes & _STORAGE_POLICY_CODES:
            return DetectionTrainingEnvironmentDecision.BLOCKED_BY_STORAGE_POLICY
        if error_codes & _DEPENDENCY_POLICY_CODES:
            return DetectionTrainingEnvironmentDecision.BLOCKED_BY_DEPENDENCY_POLICY
        if error_codes & _POLICY_CODES:
            return DetectionTrainingEnvironmentDecision.BLOCKED_BY_POLICY
        if status == DetectionTrainingEnvironmentStatus.WARNING:
            return DetectionTrainingEnvironmentDecision.NEEDS_MANUAL_SETUP
        return DetectionTrainingEnvironmentDecision.ENVIRONMENT_READY

    @staticmethod
    def _find_spec_safely(module_name: str) -> bool:
        try:
            return importlib.util.find_spec(module_name) is not None
        except (ImportError, ValueError):
            return False

    @staticmethod
    def _is_inside_repo(path: Path) -> Optional[bool]:
        try:
            repo_root = Path(__file__).resolve().parents[4]
            resolved = path.resolve()
        except (OSError, IndexError):
            return None
        try:
            resolved.relative_to(repo_root)
            return True
        except ValueError:
            return False

    @staticmethod
    def _issue(
        issues: list[DetectionTrainingEnvironmentIssue],
        severity: str,
        code: str,
        message: str,
        *,
        details: Optional[dict] = None,
    ) -> None:
        issues.append(
            DetectionTrainingEnvironmentIssue(
                environment_spec_id=_PLACEHOLDER_SPEC_ID,
                severity=DetectionTrainingEnvironmentIssueSeverity(severity),
                code=code,
                message=message,
                details=details,
            )
        )
