from uuid import UUID

from blueberry_microid.application.dto.detection_training_dto import DetectionTrainingRunDTO
from blueberry_microid.application.exceptions import DetectionTrainingRunNotFoundError
from blueberry_microid.application.ports.detection_training_run_repository import DetectionTrainingRunRepositoryPort


class GetDetectionTrainingRunUseCase:
    def __init__(self, run_repository: DetectionTrainingRunRepositoryPort) -> None:
        self._run_repository = run_repository

    def execute(self, detection_training_run_id: UUID) -> DetectionTrainingRunDTO:
        run = self._run_repository.get_by_id(detection_training_run_id)
        if run is None:
            raise DetectionTrainingRunNotFoundError(
                f"detection_training_run '{detection_training_run_id}' does not exist"
            )
        return DetectionTrainingRunDTO.from_entity(run)
