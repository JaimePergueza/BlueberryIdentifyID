from __future__ import annotations

from uuid import UUID

from blueberry_microid.application.exceptions import (
    DetectionTrainingArtifactPolicyNotFoundError,
    DetectionTrainingExecutionRunNotFoundError,
)
from blueberry_microid.application.ports.annotation_bundle_file_repository import AnnotationBundleFileRepositoryPort
from blueberry_microid.application.ports.detection_training_artifact_policy_repository import (
    DetectionTrainingArtifactPolicyRepositoryPort,
)
from blueberry_microid.application.ports.detection_training_execution_run_repository import (
    DetectionTrainingExecutionRunRepositoryPort,
)
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.application.services.local_yolo_training_runner import (
    LocalYoloTrainingResult,
    LocalYoloTrainingRunner,
)
from blueberry_microid.ml.configs.local_yolo_training_runner_config import LocalYoloTrainingRunnerConfig


class RunLocalYoloTrainingUseCase:
    """Runs local/manual YOLO training and persists metadata-only artifacts.

    This use case is intentionally not exposed through the FastAPI routers.
    It exists for a local operator/CLI path only.
    """

    def __init__(
        self,
        execution_run_repository: DetectionTrainingExecutionRunRepositoryPort,
        artifact_policy_repository: DetectionTrainingArtifactPolicyRepositoryPort,
        bundle_file_repository: AnnotationBundleFileRepositoryPort,
        runner: LocalYoloTrainingRunner,
        unit_of_work: UnitOfWorkPort,
    ) -> None:
        self._execution_run_repository = execution_run_repository
        self._artifact_policy_repository = artifact_policy_repository
        self._bundle_file_repository = bundle_file_repository
        self._runner = runner
        self._unit_of_work = unit_of_work

    def execute(self, execution_run_id: UUID, config: LocalYoloTrainingRunnerConfig) -> LocalYoloTrainingResult:
        execution_run, artifact_policy, bundle_files = self._load_inputs(execution_run_id)
        result = self._runner.run(
            execution_run=execution_run,
            artifact_policy=artifact_policy,
            bundle_files=bundle_files,
            config=config,
        )
        with self._unit_of_work as uow:
            uow.detection_training_artifact_record_repository.add_many(result.records)
            uow.commit()
        return result

    def validate_only(self, execution_run_id: UUID, config: LocalYoloTrainingRunnerConfig) -> LocalYoloTrainingResult:
        execution_run, artifact_policy, bundle_files = self._load_inputs(execution_run_id)
        return self._runner.validate_only(
            execution_run=execution_run,
            artifact_policy=artifact_policy,
            bundle_files=bundle_files,
            config=config,
        )

    def _load_inputs(self, execution_run_id: UUID):
        execution_run = self._execution_run_repository.get_by_id(execution_run_id)
        if execution_run is None:
            raise DetectionTrainingExecutionRunNotFoundError(
                f"detection_training_execution_run '{execution_run_id}' does not exist"
            )
        artifact_policy = self._artifact_policy_repository.get_by_id(execution_run.artifact_policy_id)
        if artifact_policy is None:
            raise DetectionTrainingArtifactPolicyNotFoundError(
                f"detection_training_artifact_policy '{execution_run.artifact_policy_id}' does not exist"
            )
        bundle_files = self._bundle_file_repository.list_by_bundle_run_id(execution_run.annotation_bundle_run_id)
        return execution_run, artifact_policy, bundle_files
