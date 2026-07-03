from __future__ import annotations

from typing import Optional
from uuid import UUID

from blueberry_microid.application.ports.object_detection_trainer import (
    DetectionTrainingPlan,
    ObjectDetectionTrainerPort,
)
from blueberry_microid.domain.entities.annotation_bundle_file import AnnotationBundleFile
from blueberry_microid.domain.entities.annotation_bundle_run import AnnotationBundleRun
from blueberry_microid.domain.entities.annotation_quality_gate_run import AnnotationQualityGateRun
from blueberry_microid.domain.entities.detection_training_issue import DetectionTrainingIssue
from blueberry_microid.domain.enums.annotation_bundle_file_role import AnnotationBundleFileRole
from blueberry_microid.domain.enums.annotation_bundle_status import AnnotationBundleStatus
from blueberry_microid.domain.enums.annotation_quality_gate_status import AnnotationQualityGateStatus
from blueberry_microid.domain.enums.detection_training_algorithm import DetectionTrainingAlgorithm
from blueberry_microid.domain.enums.detection_training_issue_severity import DetectionTrainingIssueSeverity
from blueberry_microid.domain.enums.detection_training_mode import DetectionTrainingMode
from blueberry_microid.domain.enums.detection_training_status import DetectionTrainingStatus
from blueberry_microid.ml.configs.detection_training_config import DetectionTrainingConfig

_PLACEHOLDER_RUN_ID = UUID("00000000-0000-0000-0000-000000000000")


class YoloDryRunTrainer(ObjectDetectionTrainerPort):
    """Plans a YOLO-style detection training attempt without ever training.

    Never calls subprocess, never imports ultralytics or torch, never
    downloads weights, never checks for a GPU, and never writes a real
    training output directory. It only inspects already-persisted
    `AnnotationBundleFile` metadata and text-level bundle state to decide
    whether a future, separately-approved training phase *could* run, and
    describes that plan as plain JSON.
    """

    def plan_training(
        self,
        bundle_run: AnnotationBundleRun,
        bundle_files: list[AnnotationBundleFile],
        quality_gate_run: Optional[AnnotationQualityGateRun],
        config: DetectionTrainingConfig,
    ) -> DetectionTrainingPlan:
        issues: list[DetectionTrainingIssue] = []

        if config.algorithm != DetectionTrainingAlgorithm.YOLO_DRY_RUN:
            self._issue(issues, "error", "unsupported_algorithm", f"unsupported algorithm: {config.algorithm}")
        if config.mode != DetectionTrainingMode.DRY_RUN:
            self._issue(issues, "error", "unsupported_mode", f"unsupported mode: {config.mode}")

        if bundle_run.status == AnnotationBundleStatus.FAILED:
            self._issue(issues, "error", "bundle_not_completed", "annotation bundle run failed")
        elif bundle_run.status == AnnotationBundleStatus.DRY_RUN:
            self._issue(issues, "error", "bundle_not_completed", "annotation bundle is dry-run only, not completed")

        if config.require_quality_gate_passed:
            if quality_gate_run is None:
                self._issue(issues, "error", "quality_gate_missing", "no annotation quality gate run was provided")
            elif quality_gate_run.status != AnnotationQualityGateStatus.PASSED:
                self._issue(
                    issues,
                    "error",
                    "quality_gate_not_passed",
                    f"annotation quality gate status is '{quality_gate_run.status.value}', not 'passed'",
                )

        files_by_role: dict[AnnotationBundleFileRole, list[AnnotationBundleFile]] = {}
        for file in bundle_files:
            files_by_role.setdefault(file.file_role, []).append(file)

        if config.require_dataset_yaml and not files_by_role.get(AnnotationBundleFileRole.DATASET_YAML):
            self._issue(issues, "error", "dataset_yaml_missing", "bundle does not contain a dataset.yaml file")
        if config.require_yolo_labels and not files_by_role.get(AnnotationBundleFileRole.YOLO_LABEL):
            self._issue(issues, "error", "yolo_labels_missing", "bundle does not contain YOLO label files")
        if config.require_coco_annotations and not files_by_role.get(AnnotationBundleFileRole.COCO_ANNOTATIONS):
            self._issue(issues, "error", "coco_annotations_missing", "bundle does not contain COCO annotations")

        errors = [issue for issue in issues if issue.severity == DetectionTrainingIssueSeverity.ERROR]
        is_runnable = not errors
        status = DetectionTrainingStatus.PLANNED if is_runnable else DetectionTrainingStatus.BLOCKED

        dataset_yaml_files = files_by_role.get(AnnotationBundleFileRole.DATASET_YAML, [])
        yolo_label_files = files_by_role.get(AnnotationBundleFileRole.YOLO_LABEL, [])
        dataset_summary = {
            "dataset_yaml_present": bool(dataset_yaml_files),
            "dataset_yaml_path": dataset_yaml_files[0].relative_path if dataset_yaml_files else None,
            "yolo_label_file_count": len(yolo_label_files),
            "coco_annotations_present": bool(files_by_role.get(AnnotationBundleFileRole.COCO_ANNOTATIONS)),
            "bundle_status": bundle_run.status.value,
            "bundle_image_count": bundle_run.image_count,
            "bundle_annotation_count": bundle_run.annotation_count,
            "bundle_label_count": bundle_run.label_count,
        }
        quality_gate_summary = (
            {
                "quality_gate_run_id": str(quality_gate_run.id),
                "status": quality_gate_run.status.value,
                "is_passed": quality_gate_run.is_passed,
                "error_count": quality_gate_run.error_count,
                "warning_count": quality_gate_run.warning_count,
            }
            if quality_gate_run is not None
            else {"quality_gate_run_id": None, "status": None, "is_passed": False}
        )

        if not is_runnable:
            training_plan: dict = {"is_runnable": False, "reason": "prerequisites_not_met"}
            command_preview: dict = {"dry_run_only": True, "command": None}
            expected_outputs: dict = {}
        else:
            dataset_yaml_path = dataset_yaml_files[0].relative_path
            command = (
                f"yolo detect train data={dataset_yaml_path} imgsz={config.image_size} "
                f"epochs={config.epochs} batch={config.batch_size} device={config.device} seed={config.seed}"
            )
            training_plan = {
                "algorithm": config.algorithm.value,
                "mode": config.mode.value,
                "planned_model_family": config.planned_model_family,
                "planned_model_variant": config.planned_model_variant,
                "image_size": config.image_size,
                "epochs": config.epochs,
                "batch_size": config.batch_size,
                "patience": config.patience,
                "seed": config.seed,
                "device": config.device,
                "workers": config.workers,
                "dataset_yaml_path": dataset_yaml_path,
            }
            command_preview = {
                "tool": "ultralytics_yolo",
                "action": "train",
                "dry_run_only": True,
                "command": command,
            }
            planned_run_dir = config.output_dir or "planned_runs/yolo_dry_run"
            expected_outputs = {
                "weights_path_planned": f"{planned_run_dir}/weights/best.pt",
                "metrics_path_planned": f"{planned_run_dir}/results.csv",
                "predictions_path_planned": f"{planned_run_dir}/predictions",
                "run_dir_planned": planned_run_dir,
            }
            self._issue(
                issues,
                "info",
                "no_training_executed",
                "this run only planned a dry-run; no training was executed",
            )

        if config.allow_external_weights:
            self._issue(
                issues,
                "warning",
                "external_weights_requested",
                "allow_external_weights=true was requested; no weights were downloaded",
                details={"pretrained_weights_path": config.pretrained_weights_path},
            )

        return DetectionTrainingPlan(
            is_runnable=is_runnable,
            status=status,
            training_plan=training_plan,
            command_preview=command_preview,
            dataset_summary=dataset_summary,
            quality_gate_summary=quality_gate_summary,
            expected_outputs=expected_outputs,
            issues=issues,
        )

    @staticmethod
    def _issue(
        issues: list[DetectionTrainingIssue],
        severity: str,
        code: str,
        message: str,
        *,
        details: Optional[dict] = None,
    ) -> None:
        issues.append(
            DetectionTrainingIssue(
                detection_training_run_id=_PLACEHOLDER_RUN_ID,
                severity=DetectionTrainingIssueSeverity(severity),
                code=code,
                message=message,
                details=details,
            )
        )
