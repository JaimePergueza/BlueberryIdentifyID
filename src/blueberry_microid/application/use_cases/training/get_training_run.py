from uuid import UUID

from blueberry_microid.application.dto.training_run_dto import TrainingRunDTO
from blueberry_microid.application.exceptions import TrainingRunNotFoundError
from blueberry_microid.application.ports.training_run_repository import TrainingRunRepositoryPort


class GetTrainingRunUseCase:
    def __init__(self, training_run_repository: TrainingRunRepositoryPort) -> None:
        self._training_run_repository = training_run_repository

    def execute(self, training_run_id: UUID) -> TrainingRunDTO:
        run = self._training_run_repository.get_by_id(training_run_id)
        if run is None:
            raise TrainingRunNotFoundError(f"training_run '{training_run_id}' does not exist")
        return TrainingRunDTO.from_entity(run)
