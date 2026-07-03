from uuid import UUID

from blueberry_microid.application.dto.training_run_dto import TrainingPredictionDTO
from blueberry_microid.application.exceptions import TrainingRunNotFoundError
from blueberry_microid.application.ports.training_prediction_repository import TrainingPredictionRepositoryPort
from blueberry_microid.application.ports.training_run_repository import TrainingRunRepositoryPort
from blueberry_microid.domain.enums.dataset_split import DatasetSplit


class ListTrainingPredictionsUseCase:
    def __init__(
        self,
        training_run_repository: TrainingRunRepositoryPort,
        training_prediction_repository: TrainingPredictionRepositoryPort,
    ) -> None:
        self._training_run_repository = training_run_repository
        self._training_prediction_repository = training_prediction_repository

    def execute(self, training_run_id: UUID, split: DatasetSplit | None = None) -> list[TrainingPredictionDTO]:
        if self._training_run_repository.get_by_id(training_run_id) is None:
            raise TrainingRunNotFoundError(f"training_run '{training_run_id}' does not exist")
        if split is None:
            predictions = self._training_prediction_repository.list_by_training_run_id(training_run_id)
        else:
            predictions = self._training_prediction_repository.list_by_training_run_id_and_split(training_run_id, split)
        return [TrainingPredictionDTO.from_entity(prediction) for prediction in predictions]
