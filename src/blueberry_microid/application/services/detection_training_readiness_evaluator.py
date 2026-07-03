from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import UUID

from blueberry_microid.domain.entities.annotation_bundle_file import AnnotationBundleFile
from blueberry_microid.domain.entities.annotation_bundle_run import AnnotationBundleRun
from blueberry_microid.domain.entities.annotation_quality_gate_issue import AnnotationQualityGateIssue
from blueberry_microid.domain.entities.annotation_quality_gate_run import AnnotationQualityGateRun
from blueberry_microid.domain.entities.detection_training_issue import DetectionTrainingIssue
from blueberry_microid.domain.entities.detection_training_readiness_issue import DetectionTrainingReadinessIssue
from blueberry_microid.domain.entities.detection_training_run import DetectionTrainingRun
from blueberry_microid.domain.enums.annotation_bundle_file_role import AnnotationBundleFileRole
from blueberry_microid.domain.enums.annotation_bundle_status import AnnotationBundleStatus
from blueberry_microid.domain.enums.annotation_quality_gate_status import AnnotationQualityGateStatus
from blueberry_microid.domain.enums.detection_training_readiness_decision import DetectionTrainingReadinessDecision
from blueberry_microid.domain.enums.detection_training_readiness_issue_severity import (
    DetectionTrainingReadinessIssueSeverity,
)
from blueberry_microid.domain.enums.detection_training_readiness_status import DetectionTrainingReadinessStatus
from blueberry_microid.domain.enums.detection_training_status import DetectionTrainingStatus
from blueberry_microid.ml.configs.detection_training_readiness_config import DetectionTrainingReadinessConfig

_PLACEHOLDER_REPORT_ID = UUID("00000000-0000-0000-0000-000000000000")
_FORBIDDEN_TERMS = ("bacteria", "fungi", "fungus", "colony", "species", "genus", "taxon", "diagnosis")
_ALLOWED_CATEGORY = "candidate_region"

_CONTRACT_CODES = {"detection_training_not_planned"}
_QUALITY_CODES = {
    "bundle_not_completed",
    "quality_gate_missing",
    "quality_gate_not_passed",
    "dataset_yaml_missing",
    "yolo_labels_missing",
}
_ENVIRONMENT_CODES = {"ultralytics_not_installed", "torch_not_installed", "gpu_not_configured", "training_executor_missing"}
_CONFIGURATION_CODES = {"taxonomy_not_allowed"}
_DATA_CODES = {
    "insufficient_total_images",
    "insufficient_total_annotations",
    "insufficient_train_images",
    "insufficient_validation_images",
    "insufficient_test_images",
    "insufficient_train_annotations",
    "insufficient_validation_annotations",
    "insufficient_test_annotations",
}


@dataclass(frozen=True)
class DetectionTrainingReadinessEvaluation:
    decision: DetectionTrainingReadinessDecision
    status: DetectionTrainingReadinessStatus
    is_ready: bool
    data_summary: dict[str, Any]
    split_summary: dict[str, Any]
    quality_summary: dict[str, Any]
    environment_summary: dict[str, Any]
    contract_summary: dict[str, Any]
    risk_summary: dict[str, Any]
    recommendation_summary: dict[str, Any]
    issues: list[DetectionTrainingReadinessIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[DetectionTrainingReadinessIssue]:
        return [issue for issue in self.issues if issue.severity == DetectionTrainingReadinessIssueSeverity.ERROR]

    @property
    def warnings(self) -> list[DetectionTrainingReadinessIssue]:
        return [issue for issue in self.issues if issue.severity == DetectionTrainingReadinessIssueSeverity.WARNING]

    @property
    def infos(self) -> list[DetectionTrainingReadinessIssue]:
        return [issue for issue in self.issues if issue.severity == DetectionTrainingReadinessIssueSeverity.INFO]


class DetectionTrainingReadinessEvaluator:
    """Evaluates whether a DetectionTrainingRun is technically ready for a
    future real training phase.

    Purely an inspection of already-persisted metadata: it never trains,
    never calls subprocess, never imports `ultralytics`/`torch`, never
    queries a GPU, never modifies files, and never downloads anything.
    `ready_for_training` never asserts scientific sufficiency or a trained
    model — only that the configured technical checks passed.
    """

    def evaluate(
        self,
        detection_training_run: DetectionTrainingRun,
        detection_training_issues: list[DetectionTrainingIssue],
        bundle_run: Optional[AnnotationBundleRun],
        bundle_files: list[AnnotationBundleFile],
        quality_gate_run: Optional[AnnotationQualityGateRun],
        quality_gate_issues: list[AnnotationQualityGateIssue],
        config: DetectionTrainingReadinessConfig,
    ) -> DetectionTrainingReadinessEvaluation:
        issues: list[DetectionTrainingReadinessIssue] = []

        self._evaluate_dry_run_state(detection_training_run, config, issues)
        self._evaluate_bundle(bundle_run, bundle_files, config, issues)
        files_by_role = self._files_by_role(bundle_files)
        self._evaluate_quality_gate(quality_gate_run, config, issues)
        data_summary, split_summary = self._evaluate_minimum_data(quality_gate_run, config, issues)
        self._evaluate_contract(detection_training_run, config, issues)
        self._evaluate_environment(config, issues)
        self._evaluate_categories(quality_gate_run, issues)

        status = self._status(issues)
        decision = self._decision(issues, status)
        is_ready = status in {
            DetectionTrainingReadinessStatus.READY,
            DetectionTrainingReadinessStatus.WARNING,
        } and decision == DetectionTrainingReadinessDecision.READY_FOR_TRAINING

        quality_summary = self._quality_summary(bundle_run, quality_gate_run, files_by_role, config)
        environment_summary = self._environment_summary(config)
        contract_summary = self._contract_summary(detection_training_run)
        risk_summary = self._risk_summary(issues)
        recommendation_summary = self._recommendation_summary(issues)

        return DetectionTrainingReadinessEvaluation(
            decision=decision,
            status=status,
            is_ready=is_ready,
            data_summary=data_summary,
            split_summary=split_summary,
            quality_summary=quality_summary,
            environment_summary=environment_summary,
            contract_summary=contract_summary,
            risk_summary=risk_summary,
            recommendation_summary=recommendation_summary,
            issues=issues,
        )

    # -- A. dry-run state -----------------------------------------------

    def _evaluate_dry_run_state(
        self,
        run: DetectionTrainingRun,
        config: DetectionTrainingReadinessConfig,
        issues: list[DetectionTrainingReadinessIssue],
    ) -> None:
        if not config.require_detection_training_planned:
            return
        if run.status != DetectionTrainingStatus.PLANNED or not run.is_runnable:
            self._issue(
                issues,
                "error",
                "detection_training_not_planned",
                f"detection_training_run status is '{run.status.value}' (is_runnable={run.is_runnable}), "
                "not a valid planned dry-run",
            )

    # -- B. bundle --------------------------------------------------------

    def _evaluate_bundle(
        self,
        bundle_run: Optional[AnnotationBundleRun],
        bundle_files: list[AnnotationBundleFile],
        config: DetectionTrainingReadinessConfig,
        issues: list[DetectionTrainingReadinessIssue],
    ) -> None:
        files_by_role = self._files_by_role(bundle_files)
        if bundle_run is None:
            if config.require_bundle_completed:
                self._issue(issues, "error", "bundle_not_completed", "no annotation bundle run was provided")
            return

        if config.require_bundle_completed and bundle_run.status != AnnotationBundleStatus.COMPLETED:
            self._issue(
                issues,
                "error",
                "bundle_not_completed",
                f"annotation bundle run status is '{bundle_run.status.value}', not 'completed'",
            )
        if config.require_dataset_yaml and not files_by_role.get(AnnotationBundleFileRole.DATASET_YAML):
            self._issue(issues, "error", "dataset_yaml_missing", "bundle does not contain a dataset.yaml file")
        if config.require_yolo_labels and not files_by_role.get(AnnotationBundleFileRole.YOLO_LABEL):
            self._issue(issues, "error", "yolo_labels_missing", "bundle does not contain YOLO label files")
        if config.warn_if_copy_images_disabled and not bool(bundle_run.config.get("copy_images", False)):
            self._issue(
                issues,
                "warning",
                "copy_images_disabled",
                "bundle was generated with copy_images=false: the bundle is not self-contained",
            )

    # -- C. quality gate ----------------------------------------------------

    def _evaluate_quality_gate(
        self,
        quality_gate_run: Optional[AnnotationQualityGateRun],
        config: DetectionTrainingReadinessConfig,
        issues: list[DetectionTrainingReadinessIssue],
    ) -> None:
        if not config.require_quality_gate_passed:
            return
        if quality_gate_run is None:
            self._issue(issues, "error", "quality_gate_missing", "no annotation quality gate run was provided")
            return
        if quality_gate_run.status != AnnotationQualityGateStatus.PASSED:
            self._issue(
                issues,
                "error",
                "quality_gate_not_passed",
                f"annotation quality gate status is '{quality_gate_run.status.value}', not 'passed'",
                details={
                    "error_count": quality_gate_run.error_count,
                    "warning_count": quality_gate_run.warning_count,
                },
            )

    # -- D. minimum data ------------------------------------------------

    def _evaluate_minimum_data(
        self,
        quality_gate_run: Optional[AnnotationQualityGateRun],
        config: DetectionTrainingReadinessConfig,
        issues: list[DetectionTrainingReadinessIssue],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not config.require_minimum_data:
            return {"checked": False}, {"checked": False}

        if quality_gate_run is None:
            severity = "error" if config.strict_mode else "warning"
            self._issue(
                issues,
                severity,
                "insufficient_total_images",
                "total image/annotation counts cannot be determined without an annotation quality gate run",
            )
            return (
                {"checked": True, "determinable": False, "total_images": 0, "total_annotations": 0},
                {"checked": True, "determinable": False},
            )

        total_images = quality_gate_run.total_images
        total_annotations = quality_gate_run.total_annotations
        if total_images < config.min_total_images:
            self._issue(
                issues,
                "error",
                "insufficient_total_images",
                f"total_images={total_images} is below the configured minimum {config.min_total_images}",
            )
        if total_annotations < config.min_total_annotations:
            self._issue(
                issues,
                "error",
                "insufficient_total_annotations",
                f"total_annotations={total_annotations} is below the configured minimum {config.min_total_annotations}",
            )

        splits = {
            "train": (
                quality_gate_run.train_image_count,
                config.min_train_images,
                quality_gate_run.train_annotation_count,
                config.min_train_annotations,
                "insufficient_train_images",
                "insufficient_train_annotations",
            ),
            "validation": (
                quality_gate_run.validation_image_count,
                config.min_validation_images,
                quality_gate_run.validation_annotation_count,
                config.min_validation_annotations,
                "insufficient_validation_images",
                "insufficient_validation_annotations",
            ),
            "test": (
                quality_gate_run.test_image_count,
                config.min_test_images,
                quality_gate_run.test_annotation_count,
                config.min_test_annotations,
                "insufficient_test_images",
                "insufficient_test_annotations",
            ),
        }
        split_summary: dict[str, Any] = {}
        for split, (images, min_images, annotations, min_annotations, image_code, annotation_code) in splits.items():
            split_summary[split] = {
                "images": images,
                "min_images": min_images,
                "annotations": annotations,
                "min_annotations": min_annotations,
            }
            if images < min_images:
                self._issue(
                    issues,
                    "error",
                    image_code,
                    f"{split} image count {images} is below the configured minimum {min_images}",
                    split=split,
                )
            if annotations < min_annotations:
                self._issue(
                    issues,
                    "error",
                    annotation_code,
                    f"{split} annotation count {annotations} is below the configured minimum {min_annotations}",
                    split=split,
                )

        data_summary = {
            "checked": True,
            "determinable": True,
            "total_images": total_images,
            "min_total_images": config.min_total_images,
            "total_annotations": total_annotations,
            "min_total_annotations": config.min_total_annotations,
        }
        return data_summary, split_summary

    # -- E. contract ------------------------------------------------------

    def _evaluate_contract(
        self,
        run: DetectionTrainingRun,
        config: DetectionTrainingReadinessConfig,
        issues: list[DetectionTrainingReadinessIssue],
    ) -> None:
        if run.status != DetectionTrainingStatus.PLANNED:
            return
        self._issue(
            issues,
            "info",
            "command_preview_not_executable",
            "command_preview is an illustrative description of a future command; it is never executed",
        )
        self._issue(
            issues,
            "info",
            "expected_outputs_are_planned_only",
            "expected_outputs are planned paths only; no weights/metrics/predictions files exist yet",
        )
        self._issue(
            issues,
            "info",
            "no_training_executed",
            "no training was executed by this run or by this readiness evaluation",
        )
        if config.require_training_executor:
            self._issue(
                issues,
                "error",
                "training_executor_missing",
                "no real training executor exists yet in this codebase",
            )
        else:
            self._issue(
                issues,
                "warning",
                "training_executor_missing",
                "no real training executor exists yet; this is expected until a future approved phase",
            )

    # -- F. environment ---------------------------------------------------

    def _evaluate_environment(
        self,
        config: DetectionTrainingReadinessConfig,
        issues: list[DetectionTrainingReadinessIssue],
    ) -> None:
        # Never installs or imports anything to check these: if required,
        # there is no safe way to confirm them, so they are always reported
        # as blocked_by_environment when the config demands them.
        if config.require_ultralytics_installed:
            self._issue(
                issues,
                "error",
                "ultralytics_not_installed",
                "require_ultralytics_installed=true but this evaluator never installs or imports ultralytics "
                "to verify it",
            )
        if config.require_torch_installed:
            self._issue(
                issues,
                "error",
                "torch_not_installed",
                "require_torch_installed=true but this evaluator never imports torch to verify it",
            )
        if config.require_gpu:
            self._issue(
                issues,
                "error",
                "gpu_not_configured",
                "require_gpu=true but this evaluator never queries GPU availability via external commands",
            )
        if config.require_external_weights_policy and not config.allow_external_weights:
            self._issue(
                issues,
                "warning",
                "external_weights_policy_missing",
                "require_external_weights_policy=true but allow_external_weights is not explicitly enabled",
            )

    # -- G. categories ------------------------------------------------------

    def _evaluate_categories(
        self,
        quality_gate_run: Optional[AnnotationQualityGateRun],
        issues: list[DetectionTrainingReadinessIssue],
    ) -> None:
        if quality_gate_run is None:
            return
        for category in quality_gate_run.category_distribution or {}:
            lowered = str(category).lower()
            if any(term in lowered for term in _FORBIDDEN_TERMS):
                self._issue(
                    issues, "error", "taxonomy_not_allowed", f"taxonomic category detected: {category}"
                )
            elif category != _ALLOWED_CATEGORY:
                self._issue(
                    issues, "error", "taxonomy_not_allowed", f"category not allowed for detection training: {category}"
                )

    # -- summaries ----------------------------------------------------------

    def _quality_summary(
        self,
        bundle_run: Optional[AnnotationBundleRun],
        quality_gate_run: Optional[AnnotationQualityGateRun],
        files_by_role: dict[AnnotationBundleFileRole, list[AnnotationBundleFile]],
        config: DetectionTrainingReadinessConfig,
    ) -> dict[str, Any]:
        return {
            "bundle_status": bundle_run.status.value if bundle_run is not None else None,
            "dataset_yaml_present": bool(files_by_role.get(AnnotationBundleFileRole.DATASET_YAML)),
            "yolo_labels_present": bool(files_by_role.get(AnnotationBundleFileRole.YOLO_LABEL)),
            "copy_images_enabled": bool(bundle_run.config.get("copy_images", False)) if bundle_run is not None else None,
            "quality_gate_status": quality_gate_run.status.value if quality_gate_run is not None else None,
            "quality_gate_is_passed": quality_gate_run.is_passed if quality_gate_run is not None else False,
            "quality_gate_error_count": quality_gate_run.error_count if quality_gate_run is not None else None,
            "quality_gate_warning_count": quality_gate_run.warning_count if quality_gate_run is not None else None,
        }

    def _environment_summary(self, config: DetectionTrainingReadinessConfig) -> dict[str, Any]:
        return {
            "require_ultralytics_installed": config.require_ultralytics_installed,
            "require_torch_installed": config.require_torch_installed,
            "require_gpu": config.require_gpu,
            "allow_cpu_training_future": config.allow_cpu_training_future,
            "training_executor_available": False,
            "require_training_executor": config.require_training_executor,
        }

    def _contract_summary(self, run: DetectionTrainingRun) -> dict[str, Any]:
        return {
            "detection_training_run_status": run.status.value,
            "is_runnable": run.is_runnable,
            "command_preview_present": bool(run.command_preview),
            "expected_outputs_present": bool(run.expected_outputs),
            "command_preview_executable": False,
            "expected_outputs_are_real_files": False,
        }

    def _risk_summary(self, issues: list[DetectionTrainingReadinessIssue]) -> dict[str, Any]:
        return {
            "error_codes": sorted({issue.code for issue in issues if issue.severity.value == "error"}),
            "warning_codes": sorted({issue.code for issue in issues if issue.severity.value == "warning"}),
        }

    def _recommendation_summary(self, issues: list[DetectionTrainingReadinessIssue]) -> dict[str, Any]:
        codes = {issue.code for issue in issues}
        recommendations: list[str] = []
        if "quality_gate_not_passed" in codes or "quality_gate_missing" in codes:
            recommendations.append("resolve annotation quality gate issues before planning real training")
        if codes & _DATA_CODES:
            recommendations.append("collect more reviewed images/annotations before real training")
        if "ultralytics_not_installed" in codes:
            recommendations.append("decide and document an ultralytics installation policy before real training")
        if "torch_not_installed" in codes:
            recommendations.append("decide and document a torch installation policy before real training")
        if "gpu_not_configured" in codes:
            recommendations.append("decide a CPU/GPU training policy before real training")
        if "training_executor_missing" in codes:
            recommendations.append("implement a real training executor in a future, separately-approved phase")
        return {"next_steps": recommendations}

    @staticmethod
    def _status(issues: list[DetectionTrainingReadinessIssue]) -> DetectionTrainingReadinessStatus:
        if any(issue.severity == DetectionTrainingReadinessIssueSeverity.ERROR for issue in issues):
            return DetectionTrainingReadinessStatus.BLOCKED
        if any(issue.severity == DetectionTrainingReadinessIssueSeverity.WARNING for issue in issues):
            return DetectionTrainingReadinessStatus.WARNING
        return DetectionTrainingReadinessStatus.READY

    @staticmethod
    def _decision(
        issues: list[DetectionTrainingReadinessIssue], status: DetectionTrainingReadinessStatus
    ) -> DetectionTrainingReadinessDecision:
        error_codes = {issue.code for issue in issues if issue.severity == DetectionTrainingReadinessIssueSeverity.ERROR}
        if error_codes & _CONTRACT_CODES:
            return DetectionTrainingReadinessDecision.BLOCKED_BY_CONTRACT
        if error_codes & _QUALITY_CODES:
            return DetectionTrainingReadinessDecision.BLOCKED_BY_QUALITY
        if error_codes & _ENVIRONMENT_CODES:
            return DetectionTrainingReadinessDecision.BLOCKED_BY_ENVIRONMENT
        if error_codes & _CONFIGURATION_CODES:
            return DetectionTrainingReadinessDecision.BLOCKED_BY_CONFIGURATION
        if error_codes & _DATA_CODES:
            return DetectionTrainingReadinessDecision.NEEDS_MORE_ANNOTATIONS
        return DetectionTrainingReadinessDecision.READY_FOR_TRAINING

    @staticmethod
    def _files_by_role(
        bundle_files: list[AnnotationBundleFile],
    ) -> dict[AnnotationBundleFileRole, list[AnnotationBundleFile]]:
        grouped: dict[AnnotationBundleFileRole, list[AnnotationBundleFile]] = {}
        for file in bundle_files:
            grouped.setdefault(file.file_role, []).append(file)
        return grouped

    @staticmethod
    def _issue(
        issues: list[DetectionTrainingReadinessIssue],
        severity: str,
        code: str,
        message: str,
        *,
        split: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> None:
        merged_details = dict(details or {})
        if split is not None:
            merged_details["split"] = split
        issues.append(
            DetectionTrainingReadinessIssue(
                readiness_report_id=_PLACEHOLDER_REPORT_ID,
                severity=DetectionTrainingReadinessIssueSeverity(severity),
                code=code,
                message=message,
                details=merged_details or None,
            )
        )
