from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.training_preflight_run_repository import TrainingPreflightRunRepositoryPort
from blueberry_microid.domain.entities.training_preflight_run import TrainingPreflightRun
from blueberry_microid.infrastructure.db.models.training_preflight_run import TrainingPreflightRunModel
from blueberry_microid.infrastructure.db.repositories.mappers import training_preflight_run_to_entity


class SqlAlchemyTrainingPreflightRunRepository(TrainingPreflightRunRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add(self, preflight_run: TrainingPreflightRun) -> TrainingPreflightRun:
        model = TrainingPreflightRunModel(
            id=preflight_run.id,
            dataset_release_id=preflight_run.dataset_release_id,
            status=preflight_run.status.value,
            is_valid=preflight_run.is_valid,
            config=preflight_run.config,
            summary=preflight_run.summary,
            item_count=preflight_run.item_count,
            train_count=preflight_run.train_count,
            validation_count=preflight_run.validation_count,
            test_count=preflight_run.test_count,
            label_counts=preflight_run.label_counts,
            split_counts=preflight_run.split_counts,
            split_label_counts=preflight_run.split_label_counts,
            leakage_checks=preflight_run.leakage_checks,
            recommendation_summary=preflight_run.recommendation_summary,
            created_at=preflight_run.created_at,
            created_by=preflight_run.created_by,
            notes=preflight_run.notes,
        )
        self._session.add(model)
        self._commit_or_flush()
        self._session.refresh(model)
        return training_preflight_run_to_entity(model)

    def get_by_id(self, preflight_run_id: UUID) -> Optional[TrainingPreflightRun]:
        model = self._session.get(TrainingPreflightRunModel, preflight_run_id)
        return training_preflight_run_to_entity(model) if model is not None else None

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[TrainingPreflightRun]:
        statement = (
            select(TrainingPreflightRunModel)
            .where(TrainingPreflightRunModel.dataset_release_id == dataset_release_id)
            .order_by(TrainingPreflightRunModel.created_at.asc(), TrainingPreflightRunModel.id.asc())
        )
        models = self._session.execute(statement).scalars().all()
        return [training_preflight_run_to_entity(model) for model in models]

    def list_all(self) -> list[TrainingPreflightRun]:
        statement = select(TrainingPreflightRunModel).order_by(
            TrainingPreflightRunModel.created_at.asc(), TrainingPreflightRunModel.id.asc()
        )
        models = self._session.execute(statement).scalars().all()
        return [training_preflight_run_to_entity(model) for model in models]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
