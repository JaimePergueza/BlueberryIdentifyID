from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.training_run_comparison_repository import (
    TrainingRunComparisonRepositoryPort,
)
from blueberry_microid.domain.entities.training_run_comparison import TrainingRunComparison
from blueberry_microid.infrastructure.db.models.training_run_comparison import TrainingRunComparisonModel
from blueberry_microid.infrastructure.db.repositories.mappers import training_run_comparison_to_entity


class SqlAlchemyTrainingRunComparisonRepository(TrainingRunComparisonRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add(self, comparison: TrainingRunComparison) -> TrainingRunComparison:
        model = TrainingRunComparisonModel(
            id=comparison.id,
            dataset_release_id=comparison.dataset_release_id,
            name=comparison.name,
            description=comparison.description,
            primary_metric=comparison.primary_metric.value,
            primary_split=comparison.primary_split.value,
            selection_policy=comparison.selection_policy.value,
            selected_training_run_id=comparison.selected_training_run_id,
            comparison_summary=comparison.comparison_summary,
            warnings=comparison.warnings,
            created_at=comparison.created_at,
            created_by=comparison.created_by,
            notes=comparison.notes,
        )
        self._session.add(model)
        self._commit_or_flush()
        self._session.refresh(model)
        return training_run_comparison_to_entity(model)

    def get_by_id(self, comparison_id: UUID) -> Optional[TrainingRunComparison]:
        model = self._session.get(TrainingRunComparisonModel, comparison_id)
        return training_run_comparison_to_entity(model) if model is not None else None

    def list_all(self) -> list[TrainingRunComparison]:
        return self._list(select(TrainingRunComparisonModel))

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[TrainingRunComparison]:
        return self._list(
            select(TrainingRunComparisonModel).where(
                TrainingRunComparisonModel.dataset_release_id == dataset_release_id
            )
        )

    def _list(self, statement) -> list[TrainingRunComparison]:
        statement = statement.order_by(TrainingRunComparisonModel.created_at.asc(), TrainingRunComparisonModel.id.asc())
        return [training_run_comparison_to_entity(model) for model in self._session.execute(statement).scalars().all()]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
