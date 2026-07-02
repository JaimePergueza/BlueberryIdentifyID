from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from blueberry_microid.application.exceptions import DuplicateDatasetSplitItemError
from blueberry_microid.application.ports.dataset_split_item_repository import DatasetSplitItemRepositoryPort
from blueberry_microid.domain.entities.dataset_split_item import DatasetSplitItem
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.infrastructure.db.models.dataset_split_item import DatasetSplitItemModel
from blueberry_microid.infrastructure.db.repositories.mappers import dataset_split_item_to_entity


class SqlAlchemyDatasetSplitItemRepository(DatasetSplitItemRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add_many(self, dataset_split_items: list[DatasetSplitItem]) -> list[DatasetSplitItem]:
        models = [
            DatasetSplitItemModel(
                id=item.id,
                dataset_release_id=item.dataset_release_id,
                dataset_item_id=item.dataset_item_id,
                sample_id=item.sample_id,
                split=item.split,
                ground_truth_label=item.ground_truth_label,
                created_at=item.created_at,
            )
            for item in dataset_split_items
        ]
        self._session.add_all(models)
        try:
            self._commit_or_flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise DuplicateDatasetSplitItemError("a dataset_item already exists in this dataset_release") from exc
        for model in models:
            self._session.refresh(model)
        return [dataset_split_item_to_entity(model) for model in models]

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[DatasetSplitItem]:
        statement = (
            select(DatasetSplitItemModel)
            .where(DatasetSplitItemModel.dataset_release_id == dataset_release_id)
            .order_by(DatasetSplitItemModel.dataset_item_id.asc(), DatasetSplitItemModel.id.asc())
        )
        models = self._session.execute(statement).scalars().all()
        return [dataset_split_item_to_entity(model) for model in models]

    def list_by_split(self, dataset_release_id: UUID, split: DatasetSplit) -> list[DatasetSplitItem]:
        statement = (
            select(DatasetSplitItemModel)
            .where(
                DatasetSplitItemModel.dataset_release_id == dataset_release_id,
                DatasetSplitItemModel.split == split,
            )
            .order_by(DatasetSplitItemModel.dataset_item_id.asc(), DatasetSplitItemModel.id.asc())
        )
        models = self._session.execute(statement).scalars().all()
        return [dataset_split_item_to_entity(model) for model in models]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
