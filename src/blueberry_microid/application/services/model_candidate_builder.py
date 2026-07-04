from __future__ import annotations

from pathlib import Path
from uuid import UUID

from blueberry_microid.application.exceptions import (
    DetectionTrainingExecutionRunNotFoundError,
    DetectionTrainingArtifactPolicyNotFoundError,
)
from blueberry_microid.application.ports.detection_training_artifact_record_repository import (
    DetectionTrainingArtifactRecordRepositoryPort,
)
from blueberry_microid.application.ports.detection_training_execution_run_repository import (
    DetectionTrainingExecutionRunRepositoryPort,
)
from blueberry_microid.domain.entities.model_candidate import ModelCandidate
from blueberry_microid.domain.enums.model_candidate_kind import ModelCandidateKind
from blueberry_microid.domain.enums.model_candidate_status import ModelCandidateStatus
from blueberry_microid.ml.validation.repository_safety_validator import RepositorySafetyValidator


class ModelCandidateBuilderError(RuntimeError):
    pass


class ModelCandidateBuilder:
    def __init__(
        self,
        execution_run_repository: DetectionTrainingExecutionRunRepositoryPort,
        artifact_record_repository: DetectionTrainingArtifactRecordRepositoryPort,
        *,
        repo_root: Path,
    ) -> None:
        self._execution_runs = execution_run_repository
        self._artifact_records = artifact_record_repository
        self._repo_root = repo_root.resolve()

    def build(self, local_yolo_training_execution_run_id: UUID, *, created_by: str | None = None, notes: str | None = None) -> ModelCandidate:
        execution_run = self._execution_runs.get_by_id(local_yolo_training_execution_run_id)
        if execution_run is None:
            raise DetectionTrainingExecutionRunNotFoundError(
                f"detection training execution run not found: {local_yolo_training_execution_run_id}"
            )
        records = self._artifact_records.list_by_artifact_policy_id(execution_run.artifact_policy_id)
        if not records:
            raise DetectionTrainingArtifactPolicyNotFoundError("no artifact records found for execution policy")
        weights = [r for r in records if r.artifact_kind.value == "actual_weights" and r.artifact_path]
        best = next((r for r in weights if Path(r.artifact_path or "").name == "best.pt"), None)
        chosen = best or next((r for r in weights if Path(r.artifact_path or "").name == "last.pt"), None)
        if chosen is None:
            raise ModelCandidateBuilderError("no registered actual model weights found")
        if not chosen.checksum_sha256 or chosen.size_bytes is None:
            raise ModelCandidateBuilderError("registered model weight is missing checksum or size")
        self._ensure_external_path(chosen.artifact_path)
        metrics = next((r for r in records if r.artifact_kind.value == "actual_metrics" and r.artifact_path), None)
        config = next((r for r in records if (r.artifact_path or "").endswith("args.yaml")), None)
        if metrics and metrics.artifact_path:
            self._ensure_external_path(metrics.artifact_path)
        if config and config.artifact_path:
            self._ensure_external_path(config.artifact_path)
        return ModelCandidate(
            local_yolo_training_execution_run_id=execution_run.id,
            detection_training_run_id=execution_run.detection_training_run_id,
            candidate_kind=ModelCandidateKind.SMOKE_YOLO,
            status=ModelCandidateStatus.CREATED,
            model_artifact_path=chosen.artifact_path or "",
            model_artifact_checksum_sha256=chosen.checksum_sha256,
            model_artifact_size_bytes=chosen.size_bytes,
            metrics_artifact_path=metrics.artifact_path if metrics else None,
            config_artifact_path=config.artifact_path if config else None,
            source_summary={
                "artifact_policy_id": str(execution_run.artifact_policy_id),
                "selected_weight": Path(chosen.artifact_path or "").name,
                "best_weight_available": best is not None,
                "metadata_only": True,
            },
            created_by=created_by,
            notes=notes,
        )

    def _ensure_external_path(self, raw_path: str | None) -> None:
        if not raw_path:
            raise ModelCandidateBuilderError("artifact path is required")
        path = Path(raw_path).resolve()
        summary = RepositorySafetyValidator().validate(self._repo_root, candidate_paths=[str(path)])
        if not summary.is_safe:
            raise ModelCandidateBuilderError(f"artifact path is not safe for model candidate: {path}")
