from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.training_run_comparison_entry_repository import (
    TrainingRunComparisonEntryRepositoryPort,
)
from blueberry_microid.domain.entities.training_run_comparison_entry import TrainingRunComparisonEntry
from blueberry_microid.infrastructure.db.models.training_run_comparison_entry import TrainingRunComparisonEntryModel
from blueberry_microid.infrastructure.db.repositories.mappers import training_run_comparison_entry_to_entity


class SqlAlchemyTrainingRunComparisonEntryRepository(TrainingRunComparisonEntryRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add_many(self, entries: list[TrainingRunComparisonEntry]) -> list[TrainingRunComparisonEntry]:
        models = [
            TrainingRunComparisonEntryModel(
                id=entry.id,
                comparison_id=entry.comparison_id,
                training_run_id=entry.training_run_id,
                rank=entry.rank,
                run_kind=entry.run_kind.value,
                baseline_model_type=entry.baseline_model_type.value,
                primary_metric_value=entry.primary_metric_value,
                train_accuracy=entry.train_accuracy,
                validation_accuracy=entry.validation_accuracy,
                test_accuracy=entry.test_accuracy,
                generalization_gap=entry.generalization_gap,
                support_train=entry.support_train,
                support_validation=entry.support_validation,
                support_test=entry.support_test,
                metrics_snapshot=entry.metrics_snapshot,
                summary=entry.summary,
                created_at=entry.created_at,
            )
            for entry in entries
        ]
        self._session.add_all(models)
        self._commit_or_flush()
        for model in models:
            self._session.refresh(model)
        return [training_run_comparison_entry_to_entity(model) for model in models]

    def list_by_comparison_id(self, comparison_id: UUID) -> list[TrainingRunComparisonEntry]:
        statement = (
            select(TrainingRunComparisonEntryModel)
            .where(TrainingRunComparisonEntryModel.comparison_id == comparison_id)
            .order_by(
                TrainingRunComparisonEntryModel.rank.asc().nulls_last(),
                TrainingRunComparisonEntryModel.training_run_id.asc(),
            )
        )
        return [
            training_run_comparison_entry_to_entity(model)
            for model in self._session.execute(statement).scalars().all()
        ]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
