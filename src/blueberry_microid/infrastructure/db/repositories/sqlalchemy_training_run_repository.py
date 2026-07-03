from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.training_run_repository import TrainingRunRepositoryPort
from blueberry_microid.domain.entities.training_run import TrainingRun
from blueberry_microid.infrastructure.db.models.training_run import TrainingRunModel
from blueberry_microid.infrastructure.db.repositories.mappers import training_run_to_entity


class SqlAlchemyTrainingRunRepository(TrainingRunRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add(self, training_run: TrainingRun) -> TrainingRun:
        model = TrainingRunModel(
            id=training_run.id,
            dataset_release_id=training_run.dataset_release_id,
            preflight_run_id=training_run.preflight_run_id,
            run_kind=training_run.run_kind.value,
            baseline_model_type=training_run.baseline_model_type.value,
            status=training_run.status.value,
            experiment_name=training_run.experiment_name,
            config=training_run.config,
            baseline_state=training_run.baseline_state,
            metrics=training_run.metrics,
            summary=training_run.summary,
            started_at=training_run.started_at,
            completed_at=training_run.completed_at,
            created_at=training_run.created_at,
            created_by=training_run.created_by,
            notes=training_run.notes,
            error_message=training_run.error_message,
        )
        self._session.add(model)
        self._commit_or_flush()
        self._session.refresh(model)
        return training_run_to_entity(model)

    def get_by_id(self, training_run_id: UUID) -> Optional[TrainingRun]:
        model = self._session.get(TrainingRunModel, training_run_id)
        return training_run_to_entity(model) if model is not None else None

    def list_all(self) -> list[TrainingRun]:
        return self._list(select(TrainingRunModel))

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[TrainingRun]:
        return self._list(select(TrainingRunModel).where(TrainingRunModel.dataset_release_id == dataset_release_id))

    def list_by_preflight_run_id(self, preflight_run_id: UUID) -> list[TrainingRun]:
        return self._list(select(TrainingRunModel).where(TrainingRunModel.preflight_run_id == preflight_run_id))

    def _list(self, statement) -> list[TrainingRun]:
        statement = statement.order_by(TrainingRunModel.created_at.asc(), TrainingRunModel.id.asc())
        return [training_run_to_entity(model) for model in self._session.execute(statement).scalars().all()]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
