from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from blueberry_microid.application.exceptions import DuplicateDatasetSnapshotError
from blueberry_microid.application.ports.dataset_snapshot_repository import DatasetSnapshotRepositoryPort
from blueberry_microid.domain.entities.dataset_snapshot import DatasetSnapshot
from blueberry_microid.infrastructure.db.models.dataset_snapshot import DatasetSnapshotModel
from blueberry_microid.infrastructure.db.repositories.mappers import dataset_snapshot_to_entity


class SqlAlchemyDatasetSnapshotRepository(DatasetSnapshotRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add(self, dataset_snapshot: DatasetSnapshot) -> DatasetSnapshot:
        model = DatasetSnapshotModel(
            id=dataset_snapshot.id,
            name=dataset_snapshot.name,
            version=dataset_snapshot.version,
            description=dataset_snapshot.description,
            created_at=dataset_snapshot.created_at,
            created_by=dataset_snapshot.created_by,
            selection_criteria=dataset_snapshot.selection_criteria,
            item_count=dataset_snapshot.item_count,
            label_distribution=dataset_snapshot.label_distribution,
            notes=dataset_snapshot.notes,
        )
        self._session.add(model)
        try:
            self._commit_or_flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise DuplicateDatasetSnapshotError(
                f"dataset snapshot '{dataset_snapshot.name}' version '{dataset_snapshot.version}' already exists"
            ) from exc
        self._session.refresh(model)
        return dataset_snapshot_to_entity(model)

    def get_by_id(self, dataset_snapshot_id: UUID) -> Optional[DatasetSnapshot]:
        model = self._session.get(DatasetSnapshotModel, dataset_snapshot_id)
        return dataset_snapshot_to_entity(model) if model is not None else None

    def list_all(self) -> list[DatasetSnapshot]:
        statement = select(DatasetSnapshotModel).order_by(
            DatasetSnapshotModel.created_at.asc(),
            DatasetSnapshotModel.id.asc(),
        )
        models = self._session.execute(statement).scalars().all()
        return [dataset_snapshot_to_entity(model) for model in models]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
