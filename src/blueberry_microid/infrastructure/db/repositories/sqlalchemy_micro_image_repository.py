from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.micro_image_repository import MicroImageRepositoryPort
from blueberry_microid.domain.entities.micro_image import MicroImage
from blueberry_microid.infrastructure.db.models.micro_image import MicroImageModel
from blueberry_microid.infrastructure.db.repositories.mappers import micro_image_to_entity


class SqlAlchemyMicroImageRepository(MicroImageRepositoryPort):
    """SQLAlchemy-backed MicroImageRepositoryPort."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, micro_image: MicroImage) -> MicroImage:
        model = MicroImageModel(
            id=micro_image.id,
            sample_id=micro_image.sample_id,
            file_path=micro_image.file_path,
            file_name=micro_image.file_name,
            mime_type=micro_image.mime_type,
            file_size_bytes=micro_image.file_size_bytes,
            width=micro_image.width,
            height=micro_image.height,
            captured_at=micro_image.captured_at,
            magnification=micro_image.magnification,
            microscope_type=micro_image.microscope_type,
            staining_method=micro_image.staining_method,
            preparation_method=micro_image.preparation_method,
            observed_structures=micro_image.observed_structures,
            notes=micro_image.notes,
            created_at=micro_image.created_at,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return micro_image_to_entity(model)

    def get_by_id(self, micro_image_id: UUID) -> Optional[MicroImage]:
        model = self._session.get(MicroImageModel, micro_image_id)
        return micro_image_to_entity(model) if model is not None else None

    def list_by_sample_id(self, sample_id: UUID) -> list[MicroImage]:
        statement = select(MicroImageModel).where(MicroImageModel.sample_id == sample_id)
        models = self._session.execute(statement).scalars().all()
        return [micro_image_to_entity(model) for model in models]
