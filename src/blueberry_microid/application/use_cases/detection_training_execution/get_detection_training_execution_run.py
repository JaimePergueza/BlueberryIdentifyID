from uuid import UUID

from blueberry_microid.application.dto.detection_training_execution_dto import DetectionTrainingExecutionRunDTO
from blueberry_microid.application.exceptions import DetectionTrainingExecutionRunNotFoundError
from blueberry_microid.application.ports.detection_training_execution_run_repository import (
    DetectionTrainingExecutionRunRepositoryPort,
)


class GetDetectionTrainingExecutionRunUseCase:
    def __init__(self, execution_run_repository: DetectionTrainingExecutionRunRepositoryPort) -> None:
        self._execution_run_repository = execution_run_repository

    def execute(self, execution_run_id: UUID) -> DetectionTrainingExecutionRunDTO:
        run = self._execution_run_repository.get_by_id(execution_run_id)
        if run is None:
            raise DetectionTrainingExecutionRunNotFoundError(
                f"detection_training_execution_run '{execution_run_id}' does not exist"
            )
        return DetectionTrainingExecutionRunDTO.from_entity(run)
