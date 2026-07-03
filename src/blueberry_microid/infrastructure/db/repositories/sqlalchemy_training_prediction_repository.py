from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.training_prediction_repository import TrainingPredictionRepositoryPort
from blueberry_microid.domain.entities.training_prediction import TrainingPrediction
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.infrastructure.db.models.training_prediction import TrainingPredictionModel
from blueberry_microid.infrastructure.db.repositories.mappers import training_prediction_to_entity


class SqlAlchemyTrainingPredictionRepository(TrainingPredictionRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add_many(self, predictions: list[TrainingPrediction]) -> list[TrainingPrediction]:
        models = [
            TrainingPredictionModel(
                id=prediction.id,
                training_run_id=prediction.training_run_id,
                dataset_split_item_id=prediction.dataset_split_item_id,
                dataset_item_id=prediction.dataset_item_id,
                split=prediction.split.value,
                ground_truth_label=prediction.ground_truth_label.value,
                predicted_label=prediction.predicted_label.value,
                is_correct=prediction.is_correct,
                created_at=prediction.created_at,
            )
            for prediction in predictions
        ]
        self._session.add_all(models)
        self._commit_or_flush()
        for model in models:
            self._session.refresh(model)
        return [training_prediction_to_entity(model) for model in models]

    def list_by_training_run_id(self, training_run_id: UUID) -> list[TrainingPrediction]:
        return self._list(select(TrainingPredictionModel).where(TrainingPredictionModel.training_run_id == training_run_id))

    def list_by_training_run_id_and_split(self, training_run_id: UUID, split: DatasetSplit) -> list[TrainingPrediction]:
        return self._list(
            select(TrainingPredictionModel).where(
                TrainingPredictionModel.training_run_id == training_run_id,
                TrainingPredictionModel.split == split.value,
            )
        )

    def _list(self, statement) -> list[TrainingPrediction]:
        statement = statement.order_by(TrainingPredictionModel.split.asc(), TrainingPredictionModel.dataset_split_item_id.asc())
        return [training_prediction_to_entity(model) for model in self._session.execute(statement).scalars().all()]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
