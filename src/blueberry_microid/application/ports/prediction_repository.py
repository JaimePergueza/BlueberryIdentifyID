from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.prediction import Prediction


class PredictionRepositoryPort(ABC):
    """Persistence contract for Prediction, independent of any ORM."""

    @abstractmethod
    def add(self, prediction: Prediction) -> Prediction:
        """Persist a new prediction. Raises DuplicatePredictionError if the
        referenced analysis_run_id already has one (1:1 relationship)."""
        raise NotImplementedError

    @abstractmethod
    def get_by_analysis_run_id(self, analysis_run_id: UUID) -> Optional[Prediction]:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, prediction_id: UUID) -> Optional[Prediction]:
        raise NotImplementedError
