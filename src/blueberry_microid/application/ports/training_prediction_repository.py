from abc import ABC, abstractmethod
from uuid import UUID

from blueberry_microid.domain.entities.training_prediction import TrainingPrediction
from blueberry_microid.domain.enums.dataset_split import DatasetSplit


class TrainingPredictionRepositoryPort(ABC):
    @abstractmethod
    def add_many(self, predictions: list[TrainingPrediction]) -> list[TrainingPrediction]:
        raise NotImplementedError

    @abstractmethod
    def list_by_training_run_id(self, training_run_id: UUID) -> list[TrainingPrediction]:
        raise NotImplementedError

    @abstractmethod
    def list_by_training_run_id_and_split(
        self, training_run_id: UUID, split: DatasetSplit
    ) -> list[TrainingPrediction]:
        raise NotImplementedError
