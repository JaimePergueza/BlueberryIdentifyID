from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from blueberry_microid.application.exceptions import DuplicateDatasetItemError
from blueberry_microid.application.ports.dataset_item_repository import DatasetItemRepositoryPort
from blueberry_microid.domain.entities.dataset_item import DatasetItem
from blueberry_microid.infrastructure.db.models.dataset_item import DatasetItemModel
from blueberry_microid.infrastructure.db.repositories.mappers import dataset_item_to_entity


class SqlAlchemyDatasetItemRepository(DatasetItemRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add_many(self, dataset_items: list[DatasetItem]) -> list[DatasetItem]:
        models = [
            DatasetItemModel(
                id=item.id,
                dataset_snapshot_id=item.dataset_snapshot_id,
                analysis_run_id=item.analysis_run_id,
                sample_id=item.sample_id,
                petri_image_id=item.petri_image_id,
                micro_image_id=item.micro_image_id,
                prediction_id=item.prediction_id,
                final_review_id=item.final_review_id,
                curation_run_id=item.curation_run_id,
                curation_item_id=item.curation_item_id,
                ground_truth_label=item.ground_truth_label,
                source_review_decision=item.source_review_decision,
                included=item.included,
                exclusion_reason=item.exclusion_reason,
                provenance=item.provenance,
                created_at=item.created_at,
            )
            for item in dataset_items
        ]
        self._session.add_all(models)
        try:
            self._commit_or_flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise DuplicateDatasetItemError("analysis_run already exists in this dataset snapshot") from exc
        for model in models:
            self._session.refresh(model)
        return [dataset_item_to_entity(model) for model in models]

    def list_by_dataset_snapshot_id(self, dataset_snapshot_id: UUID) -> list[DatasetItem]:
        statement = (
            select(DatasetItemModel)
            .where(DatasetItemModel.dataset_snapshot_id == dataset_snapshot_id)
            .order_by(DatasetItemModel.analysis_run_id.asc(), DatasetItemModel.id.asc())
        )
        models = self._session.execute(statement).scalars().all()
        return [dataset_item_to_entity(model) for model in models]

    def count_by_dataset_snapshot_id(self, dataset_snapshot_id: UUID) -> int:
        statement = select(func.count()).select_from(DatasetItemModel).where(
            DatasetItemModel.dataset_snapshot_id == dataset_snapshot_id,
            DatasetItemModel.included.is_(True),
        )
        return int(self._session.execute(statement).scalar_one())

    def label_distribution_by_dataset_snapshot_id(self, dataset_snapshot_id: UUID) -> dict[str, int]:
        statement = (
            select(DatasetItemModel.ground_truth_label, func.count())
            .where(
                DatasetItemModel.dataset_snapshot_id == dataset_snapshot_id,
                DatasetItemModel.included.is_(True),
                DatasetItemModel.ground_truth_label.is_not(None),
            )
            .group_by(DatasetItemModel.ground_truth_label)
        )
        rows = self._session.execute(statement).all()
        return {label.value: int(count) for label, count in rows}

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
