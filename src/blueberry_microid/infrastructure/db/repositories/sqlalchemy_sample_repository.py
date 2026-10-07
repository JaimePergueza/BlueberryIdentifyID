from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from blueberry_microid.application.exceptions import DuplicateSampleCodeError
from blueberry_microid.application.ports.sample_repository import SampleRepositoryPort
from blueberry_microid.domain.entities.sample import Sample
from blueberry_microid.infrastructure.db.models.sample import SampleModel
from blueberry_microid.infrastructure.db.repositories.mappers import sample_to_entity


class SqlAlchemySampleRepository(SampleRepositoryPort):
    """SQLAlchemy-backed SampleRepositoryPort.

    Standalone operations commit by default. Inside a Unit of Work,
    auto_commit=False flushes without committing the encompassing transaction.
    """

    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add(self, sample: Sample) -> Sample:
        model = SampleModel(
            id=sample.id,
            sample_code=sample.sample_code,
            product=sample.product,
            lot_code=sample.lot_code,
            origin=sample.origin,
            collection_date=sample.collection_date,
            notes=sample.notes,
            created_at=sample.created_at,
            updated_at=sample.updated_at,
        )
        self._session.add(model)
        try:
            self._session.commit() if self._auto_commit else self._session.flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise DuplicateSampleCodeError(f"sample_code '{sample.sample_code}' already exists") from exc
        self._session.refresh(model)
        return sample_to_entity(model)

    def get_by_id(self, sample_id: UUID) -> Optional[Sample]:
        model = self._session.get(SampleModel, sample_id)
        return sample_to_entity(model) if model is not None else None

    def get_by_sample_code(self, sample_code: str) -> Optional[Sample]:
        statement = select(SampleModel).where(SampleModel.sample_code == sample_code)
        model = self._session.execute(statement).scalar_one_or_none()
        return sample_to_entity(model) if model is not None else None
