from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from blueberry_microid.application.exceptions import DuplicateModelVersionError
from blueberry_microid.application.ports.model_version_repository import ModelVersionRepositoryPort
from blueberry_microid.domain.entities.model_version import ModelVersion
from blueberry_microid.infrastructure.db.models.model_version import ModelVersionModel
from blueberry_microid.infrastructure.db.repositories.mappers import model_version_to_entity


class SqlAlchemyModelVersionRepository(ModelVersionRepositoryPort):
    """SQLAlchemy-backed ModelVersionRepositoryPort."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, model_version: ModelVersion) -> ModelVersion:
        model = ModelVersionModel(
            id=model_version.id,
            name=model_version.name,
            version=model_version.version,
            model_type=model_version.model_type,
            description=model_version.description,
            is_active=model_version.is_active,
            created_at=model_version.created_at,
        )
        self._session.add(model)
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise DuplicateModelVersionError(
                f"model version '{model_version.name}' v'{model_version.version}' already exists"
            ) from exc
        self._session.refresh(model)
        return model_version_to_entity(model)

    def get_by_id(self, model_version_id: UUID) -> Optional[ModelVersion]:
        model = self._session.get(ModelVersionModel, model_version_id)
        return model_version_to_entity(model) if model is not None else None

    def list_all(self) -> list[ModelVersion]:
        statement = select(ModelVersionModel).order_by(ModelVersionModel.created_at)
        models = self._session.execute(statement).scalars().all()
        return [model_version_to_entity(model) for model in models]
