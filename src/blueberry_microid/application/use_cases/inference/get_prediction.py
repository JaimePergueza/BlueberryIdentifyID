from uuid import UUID

from blueberry_microid.application.dto.prediction_dto import PredictionDTO
from blueberry_microid.application.exceptions import PredictionNotFoundError
from blueberry_microid.application.ports.prediction_repository import PredictionRepositoryPort


class GetPredictionForAnalysisRunUseCase:
    """Reads the Prediction associated with one AnalysisRun, if any.

    Read-only: never creates or triggers anything. Raises
    `PredictionNotFoundError` if the AnalysisRun hasn't been processed yet
    (or doesn't exist — either way, there is no Prediction to return).
    """

    def __init__(self, prediction_repository: PredictionRepositoryPort) -> None:
        self._prediction_repository = prediction_repository

    def execute(self, analysis_run_id: UUID) -> PredictionDTO:
        prediction = self._prediction_repository.get_by_analysis_run_id(analysis_run_id)
        if prediction is None:
            raise PredictionNotFoundError(f"analysis_run '{analysis_run_id}' has no prediction yet")
        return PredictionDTO.from_entity(prediction)
