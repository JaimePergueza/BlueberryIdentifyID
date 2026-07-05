from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from blueberry_microid.application.exceptions import DuplicateDatasetCurationItemError
from blueberry_microid.application.ports.dataset_curation_repository import (
    DatasetCurationItemRepositoryPort,
    DatasetCurationRunRepositoryPort,
)
from blueberry_microid.domain.entities.dataset_curation_item import DatasetCurationItem
from blueberry_microid.domain.entities.dataset_curation_run import DatasetCurationRun
from blueberry_microid.domain.enums.dataset_curation_status import DatasetCurationStatus
from blueberry_microid.infrastructure.db.models.dataset_curation_item import DatasetCurationItemModel
from blueberry_microid.infrastructure.db.models.dataset_curation_run import DatasetCurationRunModel
from blueberry_microid.infrastructure.db.repositories.mappers import (
    dataset_curation_item_to_entity,
    dataset_curation_run_to_entity,
)


class SqlAlchemyDatasetCurationRunRepository(DatasetCurationRunRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add(self, curation_run: DatasetCurationRun) -> DatasetCurationRun:
        model = DatasetCurationRunModel(
            id=curation_run.id,
            status=curation_run.status,
            policy=curation_run.policy,
            total_candidates_scanned=curation_run.total_candidates_scanned,
            included_count=curation_run.included_count,
            excluded_count=curation_run.excluded_count,
            created_snapshot_id=curation_run.created_snapshot_id,
            issues=curation_run.issues,
            created_by=curation_run.created_by,
            notes=curation_run.notes,
            created_at=curation_run.created_at,
            completed_at=curation_run.completed_at,
        )
        self._session.add(model)
        self._commit_or_flush()
        self._session.refresh(model)
        return dataset_curation_run_to_entity(model)

    def get_by_id(self, curation_run_id: UUID) -> Optional[DatasetCurationRun]:
        model = self._session.get(DatasetCurationRunModel, curation_run_id)
        return dataset_curation_run_to_entity(model) if model is not None else None

    def list_all(self) -> list[DatasetCurationRun]:
        statement = select(DatasetCurationRunModel).order_by(
            DatasetCurationRunModel.created_at.asc(), DatasetCurationRunModel.id.asc()
        )
        models = self._session.execute(statement).scalars().all()
        return [dataset_curation_run_to_entity(model) for model in models]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()


class SqlAlchemyDatasetCurationItemRepository(DatasetCurationItemRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add_many(self, curation_items: list[DatasetCurationItem]) -> list[DatasetCurationItem]:
        models = [
            DatasetCurationItemModel(
                id=item.id,
                curation_run_id=item.curation_run_id,
                sample_id=item.sample_id,
                analysis_run_id=item.analysis_run_id,
                prediction_id=item.prediction_id,
                human_review_id=item.human_review_id,
                petri_image_id=item.petri_image_id,
                micro_image_id=item.micro_image_id,
                automatic_label=item.automatic_label,
                final_label=item.final_label,
                review_decision=item.review_decision,
                curation_status=item.curation_status,
                exclusion_reason=item.exclusion_reason,
                provenance=item.provenance,
                feature_summary=item.feature_summary,
                quality_summary=item.quality_summary,
                created_at=item.created_at,
            )
            for item in curation_items
        ]
        self._session.add_all(models)
        try:
            self._commit_or_flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise DuplicateDatasetCurationItemError(
                "analysis_run already exists in this dataset curation run"
            ) from exc
        for model in models:
            self._session.refresh(model)
        return [dataset_curation_item_to_entity(model) for model in models]

    def list_by_curation_run_id(
        self,
        curation_run_id: UUID,
        *,
        status: Optional[DatasetCurationStatus] = None,
    ) -> list[DatasetCurationItem]:
        statement = select(DatasetCurationItemModel).where(
            DatasetCurationItemModel.curation_run_id == curation_run_id
        )
        if status is not None:
            statement = statement.where(DatasetCurationItemModel.curation_status == status)
        statement = statement.order_by(
            DatasetCurationItemModel.analysis_run_id.asc(),
            DatasetCurationItemModel.id.asc(),
        )
        models = self._session.execute(statement).scalars().all()
        return [dataset_curation_item_to_entity(model) for model in models]

    def count_by_curation_run_id(self, curation_run_id: UUID) -> int:
        statement = select(func.count()).select_from(DatasetCurationItemModel).where(
            DatasetCurationItemModel.curation_run_id == curation_run_id
        )
        return int(self._session.execute(statement).scalar_one())

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()

