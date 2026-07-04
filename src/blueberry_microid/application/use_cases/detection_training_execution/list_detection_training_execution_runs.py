from typing import Optional
from uuid import UUID

from blueberry_microid.application.dto.detection_training_execution_dto import DetectionTrainingExecutionRunDTO
from blueberry_microid.application.ports.detection_training_execution_run_repository import (
    DetectionTrainingExecutionRunRepositoryPort,
)


class ListDetectionTrainingExecutionRunsUseCase:
    def __init__(self, execution_run_repository: DetectionTrainingExecutionRunRepositoryPort) -> None:
        self._execution_run_repository = execution_run_repository

    def execute(
        self,
        *,
        detection_training_run_id: Optional[UUID] = None,
        readiness_report_id: Optional[UUID] = None,
        environment_spec_id: Optional[UUID] = None,
        artifact_policy_id: Optional[UUID] = None,
        annotation_bundle_run_id: Optional[UUID] = None,
        dataset_release_id: Optional[UUID] = None,
    ) -> list[DetectionTrainingExecutionRunDTO]:
        if detection_training_run_id is not None:
            runs = self._execution_run_repository.list_by_detection_training_run_id(detection_training_run_id)
        elif readiness_report_id is not None:
            runs = self._execution_run_repository.list_by_readiness_report_id(readiness_report_id)
        elif environment_spec_id is not None:
            runs = self._execution_run_repository.list_by_environment_spec_id(environment_spec_id)
        elif artifact_policy_id is not None:
            runs = self._execution_run_repository.list_by_artifact_policy_id(artifact_policy_id)
        elif annotation_bundle_run_id is not None:
            runs = self._execution_run_repository.list_by_annotation_bundle_run_id(annotation_bundle_run_id)
        elif dataset_release_id is not None:
            runs = self._execution_run_repository.list_by_dataset_release_id(dataset_release_id)
        else:
            runs = self._execution_run_repository.list_all()
        return [DetectionTrainingExecutionRunDTO.from_entity(run) for run in runs]
