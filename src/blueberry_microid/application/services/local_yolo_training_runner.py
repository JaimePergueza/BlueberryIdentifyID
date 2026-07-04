from __future__ import annotations

import hashlib
import importlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from blueberry_microid.domain.entities.annotation_bundle_file import AnnotationBundleFile
from blueberry_microid.domain.entities.detection_training_artifact_policy import DetectionTrainingArtifactPolicy
from blueberry_microid.domain.entities.detection_training_artifact_record import DetectionTrainingArtifactRecord
from blueberry_microid.domain.entities.detection_training_execution_run import DetectionTrainingExecutionRun
from blueberry_microid.domain.enums.annotation_bundle_file_role import AnnotationBundleFileRole
from blueberry_microid.domain.enums.detection_training_artifact_kind import DetectionTrainingArtifactKind
from blueberry_microid.domain.enums.detection_training_artifact_location_type import (
    DetectionTrainingArtifactLocationType,
)
from blueberry_microid.domain.enums.detection_training_artifact_state import DetectionTrainingArtifactState
from blueberry_microid.domain.enums.detection_training_execution_status import DetectionTrainingExecutionStatus
from blueberry_microid.ml.configs.local_yolo_training_runner_config import LocalYoloTrainingRunnerConfig
from blueberry_microid.ml.configs.repository_safety_config import RepositorySafetyConfig
from blueberry_microid.ml.validation.repository_safety_validator import RepositorySafetyValidator

_WEIGHT_EXTENSIONS = {".pt", ".pth", ".onnx", ".h5", ".ckpt"}
_METRIC_NAMES = {"results.csv", "metrics.json", "results.json"}
_LOG_EXTENSIONS = {".log", ".txt"}
_CONFIG_NAMES = {"args.yaml", "hyp.yaml", "opt.yaml"}
_MANIFEST_NAMES = {"dataset.yaml", "data.yaml"}


class LocalYoloTrainingRunnerError(RuntimeError):
    """Raised when local/manual YOLO training is not allowed or fails."""


@dataclass(frozen=True)
class LocalYoloTrainingResult:
    execution_run_id: str
    artifact_root_dir: str
    dataset_yaml_path: str
    save_dir: str
    records: list[DetectionTrainingArtifactRecord] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


class LocalYoloTrainingRunner:
    """Experimental local/manual YOLO runner.

    This is the only module that may import `ultralytics`, and it does so
    lazily inside `run()`, after CI/manual/artifact/repository gates pass.
    It never uses subprocess and never stores artifact bytes in the DB.
    """

    def __init__(
        self,
        *,
        repo_root: Path,
        yolo_class_factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        self._repo_root = repo_root
        self._yolo_class_factory = yolo_class_factory or self._load_yolo_class

    def run(
        self,
        *,
        execution_run: DetectionTrainingExecutionRun,
        artifact_policy: DetectionTrainingArtifactPolicy,
        bundle_files: list[AnnotationBundleFile],
        config: LocalYoloTrainingRunnerConfig,
    ) -> LocalYoloTrainingResult:
        self._validate_prerequisites(execution_run, artifact_policy, config)
        artifact_root = Path(config.artifact_root_dir).resolve()
        base_model_path = Path(config.base_model_path).resolve()
        dataset_yaml_path = self._find_dataset_yaml(bundle_files).resolve()
        self._validate_paths(artifact_root, base_model_path, dataset_yaml_path, artifact_policy)

        candidate_paths = [str(artifact_root), str(base_model_path)]
        safety_report = RepositorySafetyValidator().validate(
            self._repo_root, RepositorySafetyConfig(), candidate_paths=candidate_paths
        )
        if not safety_report.is_safe:
            raise LocalYoloTrainingRunnerError("RepositorySafetyValidator did not pass")

        yolo_class = self._yolo_class_factory()
        model = yolo_class(str(base_model_path))
        training_kwargs = self._training_kwargs(config, dataset_yaml_path, artifact_root, execution_run)
        raw_result = model.train(**training_kwargs)
        save_dir = self._resolve_save_dir(raw_result, artifact_root, training_kwargs["name"])
        records = self._scan_artifacts(
            save_dir=save_dir,
            artifact_root=artifact_root,
            artifact_policy=artifact_policy,
            execution_run=execution_run,
        )
        return LocalYoloTrainingResult(
            execution_run_id=str(execution_run.id),
            artifact_root_dir=str(artifact_root),
            dataset_yaml_path=str(dataset_yaml_path),
            save_dir=str(save_dir),
            records=records,
            summary={
                "record_count": len(records),
                "artifact_kinds": sorted({record.artifact_kind.value for record in records}),
                "metadata_only": True,
                "no_binary_content_stored": True,
            },
        )

    def _validate_prerequisites(
        self,
        execution_run: DetectionTrainingExecutionRun,
        artifact_policy: DetectionTrainingArtifactPolicy,
        config: LocalYoloTrainingRunnerConfig,
    ) -> None:
        if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
            raise LocalYoloTrainingRunnerError("local YOLO training is blocked in CI")
        if config.manual_confirmation_text != config.required_confirmation_text:
            raise LocalYoloTrainingRunnerError("manual confirmation text does not match")
        if execution_run.status != DetectionTrainingExecutionStatus.READY_TO_EXECUTE:
            raise LocalYoloTrainingRunnerError("DetectionTrainingExecutionRun must be ready_to_execute")
        if execution_run.artifact_policy_id != artifact_policy.id:
            raise LocalYoloTrainingRunnerError("artifact policy does not belong to execution run")
        if not artifact_policy.is_policy_ready:
            raise LocalYoloTrainingRunnerError("artifact policy is not ready")
        if config.require_policy_allows_actual_registration:
            policy_config = artifact_policy.config or {}
            if not policy_config.get("allow_actual_artifact_registration") or not policy_config.get(
                "register_actual_artifacts"
            ):
                raise LocalYoloTrainingRunnerError("artifact policy does not allow actual artifact registration")

    def _validate_paths(
        self,
        artifact_root: Path,
        base_model_path: Path,
        dataset_yaml_path: Path,
        artifact_policy: DetectionTrainingArtifactPolicy,
    ) -> None:
        if not artifact_root.is_absolute():
            raise LocalYoloTrainingRunnerError("artifact_root_dir must be absolute")
        artifact_root.mkdir(parents=True, exist_ok=True)
        if self._is_inside(artifact_root, self._repo_root):
            raise LocalYoloTrainingRunnerError("artifact_root_dir must be outside the repository")
        policy_root = artifact_policy.artifact_root_dir
        if policy_root and artifact_root != Path(policy_root).resolve():
            raise LocalYoloTrainingRunnerError("artifact_root_dir does not match artifact policy")
        if not base_model_path.is_file():
            raise LocalYoloTrainingRunnerError("base_model_path must point to an existing local file")
        if self._is_inside(base_model_path, self._repo_root):
            raise LocalYoloTrainingRunnerError("base_model_path must be outside the repository")
        if not dataset_yaml_path.is_file():
            raise LocalYoloTrainingRunnerError("dataset.yaml from bundle does not exist")

    def _find_dataset_yaml(self, bundle_files: list[AnnotationBundleFile]) -> Path:
        for bundle_file in bundle_files:
            if bundle_file.file_role == AnnotationBundleFileRole.DATASET_YAML:
                return Path(bundle_file.file_path)
        raise LocalYoloTrainingRunnerError("AnnotationBundleRun has no dataset_yaml file")

    def _training_kwargs(
        self,
        config: LocalYoloTrainingRunnerConfig,
        dataset_yaml_path: Path,
        artifact_root: Path,
        execution_run: DetectionTrainingExecutionRun,
    ) -> dict[str, Any]:
        run_name = config.run_name or f"execution-{execution_run.id}"
        kwargs: dict[str, Any] = {
            "data": str(dataset_yaml_path),
            "project": str(artifact_root),
            "name": run_name,
            "exist_ok": config.allow_existing_output_dir,
        }
        for config_name, yolo_name in (
            ("epochs", "epochs"),
            ("image_size", "imgsz"),
            ("batch_size", "batch"),
            ("device", "device"),
            ("workers", "workers"),
            ("seed", "seed"),
            ("patience", "patience"),
        ):
            value = getattr(config, config_name)
            if value is not None:
                kwargs[yolo_name] = value
        return kwargs

    def _scan_artifacts(
        self,
        *,
        save_dir: Path,
        artifact_root: Path,
        artifact_policy: DetectionTrainingArtifactPolicy,
        execution_run: DetectionTrainingExecutionRun,
    ) -> list[DetectionTrainingArtifactRecord]:
        records: list[DetectionTrainingArtifactRecord] = []
        if save_dir.exists():
            records.append(
                DetectionTrainingArtifactRecord(
                    artifact_policy_id=artifact_policy.id,
                    detection_training_run_id=execution_run.detection_training_run_id,
                    artifact_kind=DetectionTrainingArtifactKind.OTHER,
                    artifact_state=DetectionTrainingArtifactState.REGISTERED,
                    location_type=DetectionTrainingArtifactLocationType.LOCAL_PATH,
                    artifact_path=str(save_dir),
                    relative_path=self._relative_to_root(save_dir, artifact_root),
                    file_extension=None,
                    size_bytes=None,
                    checksum_sha256=None,
                    metadata={"role": "actual_run_dir", "training_execution_run_id": str(execution_run.id)},
                )
            )
        for path in sorted((p for p in save_dir.rglob("*") if p.is_file()), key=lambda p: p.as_posix()):
            if not self._is_inside(path, artifact_root):
                continue
            records.append(
                DetectionTrainingArtifactRecord(
                    artifact_policy_id=artifact_policy.id,
                    detection_training_run_id=execution_run.detection_training_run_id,
                    artifact_kind=self._classify_artifact(path),
                    artifact_state=DetectionTrainingArtifactState.REGISTERED,
                    location_type=DetectionTrainingArtifactLocationType.LOCAL_PATH,
                    artifact_path=str(path),
                    relative_path=self._relative_to_root(path, artifact_root),
                    file_extension=path.suffix.lower() or None,
                    size_bytes=path.stat().st_size,
                    checksum_sha256=self._sha256(path),
                    metadata={"training_execution_run_id": str(execution_run.id), "metadata_only": True},
                )
            )
        return records

    def _resolve_save_dir(self, raw_result: Any, artifact_root: Path, run_name: str) -> Path:
        save_dir = getattr(raw_result, "save_dir", None)
        if save_dir:
            return Path(save_dir).resolve()
        return (artifact_root / run_name).resolve()

    def _classify_artifact(self, path: Path) -> DetectionTrainingArtifactKind:
        name = path.name.lower()
        suffix = path.suffix.lower()
        if suffix in _WEIGHT_EXTENSIONS:
            return DetectionTrainingArtifactKind.ACTUAL_WEIGHTS
        if name in _METRIC_NAMES:
            return DetectionTrainingArtifactKind.ACTUAL_METRICS
        if "predict" in path.as_posix().lower():
            return DetectionTrainingArtifactKind.ACTUAL_PREDICTIONS
        if suffix in _LOG_EXTENSIONS:
            return DetectionTrainingArtifactKind.ACTUAL_LOGS
        if name in _MANIFEST_NAMES:
            return DetectionTrainingArtifactKind.ACTUAL_MANIFEST
        if name in _CONFIG_NAMES:
            return DetectionTrainingArtifactKind.OTHER
        return DetectionTrainingArtifactKind.OTHER

    def _load_yolo_class(self) -> Any:
        module = importlib.import_module("ultralytics")
        return module.YOLO

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _relative_to_root(path: Path, artifact_root: Path) -> str:
        return path.resolve().relative_to(artifact_root.resolve()).as_posix()

    @staticmethod
    def _is_inside(path: Path, root: Path) -> bool:
        try:
            path.resolve().relative_to(root.resolve())
            return True
        except ValueError:
            return False
