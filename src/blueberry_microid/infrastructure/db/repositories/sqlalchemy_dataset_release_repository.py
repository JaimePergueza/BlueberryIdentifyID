from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.dataset_release_repository import DatasetReleaseRepositoryPort
from blueberry_microid.domain.entities.dataset_release import DatasetRelease
from blueberry_microid.infrastructure.db.models.dataset_release import DatasetReleaseModel
from blueberry_microid.infrastructure.db.repositories.mappers import dataset_release_to_entity


class SqlAlchemyDatasetReleaseRepository(DatasetReleaseRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add(self, dataset_release: DatasetRelease) -> DatasetRelease:
        model = DatasetReleaseModel(
            id=dataset_release.id,
            dataset_snapshot_id=dataset_release.dataset_snapshot_id,
            name=dataset_release.name,
            version=dataset_release.version,
            split_strategy=dataset_release.split_strategy,
            random_seed=dataset_release.random_seed,
            train_ratio=dataset_release.train_ratio,
            validation_ratio=dataset_release.validation_ratio,
            test_ratio=dataset_release.test_ratio,
            item_count=dataset_release.item_count,
            train_count=dataset_release.train_count,
            validation_count=dataset_release.validation_count,
            test_count=dataset_release.test_count,
            label_distribution=dataset_release.label_distribution,
            split_distribution=dataset_release.split_distribution,
            created_at=dataset_release.created_at,
            created_by=dataset_release.created_by,
            notes=dataset_release.notes,
        )
        self._session.add(model)
        self._commit_or_flush()
        self._session.refresh(model)
        return dataset_release_to_entity(model)

    def get_by_id(self, dataset_release_id: UUID) -> Optional[DatasetRelease]:
        model = self._session.get(DatasetReleaseModel, dataset_release_id)
        return dataset_release_to_entity(model) if model is not None else None

    def list_by_dataset_snapshot_id(self, dataset_snapshot_id: UUID) -> list[DatasetRelease]:
        statement = (
            select(DatasetReleaseModel)
            .where(DatasetReleaseModel.dataset_snapshot_id == dataset_snapshot_id)
            .order_by(DatasetReleaseModel.created_at.asc(), DatasetReleaseModel.id.asc())
        )
        models = self._session.execute(statement).scalars().all()
        return [dataset_release_to_entity(model) for model in models]

    def list_all(self) -> list[DatasetRelease]:
        statement = select(DatasetReleaseModel).order_by(
            DatasetReleaseModel.created_at.asc(), DatasetReleaseModel.id.asc()
        )
        models = self._session.execute(statement).scalars().all()
        return [dataset_release_to_entity(model) for model in models]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
