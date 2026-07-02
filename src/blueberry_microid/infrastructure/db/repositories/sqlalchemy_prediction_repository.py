from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from blueberry_microid.application.exceptions import DuplicatePredictionError
from blueberry_microid.application.ports.prediction_repository import PredictionRepositoryPort
from blueberry_microid.domain.entities.prediction import Prediction
from blueberry_microid.infrastructure.db.models.prediction import PredictionModel
from blueberry_microid.infrastructure.db.repositories.mappers import prediction_to_entity


class SqlAlchemyPredictionRepository(PredictionRepositoryPort):
    """SQLAlchemy-backed PredictionRepositoryPort.

    `auto_commit=False` is used only when constructed inside a
    `UnitOfWorkPort` transaction (see `sqlalchemy_unit_of_work.py`), so the
    Prediction row and the AnalysisRun's final status commit together or not
    at all. Every other caller keeps the default (`True`).
    """

    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add(self, prediction: Prediction) -> Prediction:
        model = PredictionModel(
            id=prediction.id,
            analysis_run_id=prediction.analysis_run_id,
            predicted_label=prediction.predicted_label,
            confidence_score=prediction.confidence_score,
            class_probabilities=prediction.class_probabilities,
            technical_observation=prediction.technical_observation,
            requires_human_review=prediction.requires_human_review,
            created_at=prediction.created_at,
        )
        self._session.add(model)
        try:
            self._commit_or_flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise DuplicatePredictionError(
                f"analysis_run '{prediction.analysis_run_id}' already has a prediction"
            ) from exc
        self._session.refresh(model)
        return prediction_to_entity(model)

    def get_by_analysis_run_id(self, analysis_run_id: UUID) -> Optional[Prediction]:
        statement = select(PredictionModel).where(PredictionModel.analysis_run_id == analysis_run_id)
        model = self._session.execute(statement).scalar_one_or_none()
        return prediction_to_entity(model) if model is not None else None

    def get_by_id(self, prediction_id: UUID) -> Optional[Prediction]:
        model = self._session.get(PredictionModel, prediction_id)
        return prediction_to_entity(model) if model is not None else None

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
