from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.petri_image_repository import PetriImageRepositoryPort
from blueberry_microid.domain.entities.petri_image import PetriImage
from blueberry_microid.infrastructure.db.models.petri_image import PetriImageModel
from blueberry_microid.infrastructure.db.repositories.mappers import petri_image_to_entity


class SqlAlchemyPetriImageRepository(PetriImageRepositoryPort):
    """SQLAlchemy-backed PetriImageRepositoryPort."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, petri_image: PetriImage) -> PetriImage:
        model = PetriImageModel(
            id=petri_image.id,
            sample_id=petri_image.sample_id,
            file_path=petri_image.file_path,
            file_name=petri_image.file_name,
            mime_type=petri_image.mime_type,
            file_size_bytes=petri_image.file_size_bytes,
            width=petri_image.width,
            height=petri_image.height,
            captured_at=petri_image.captured_at,
            culture_medium=petri_image.culture_medium,
            incubation_temperature_c=petri_image.incubation_temperature_c,
            incubation_time_hours=petri_image.incubation_time_hours,
            seeding_date=petri_image.seeding_date,
            observed_colony_color=petri_image.observed_colony_color,
            observed_colony_shape=petri_image.observed_colony_shape,
            observed_colony_margin=petri_image.observed_colony_margin,
            observed_colony_texture=petri_image.observed_colony_texture,
            notes=petri_image.notes,
            created_at=petri_image.created_at,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return petri_image_to_entity(model)

    def get_by_id(self, petri_image_id: UUID) -> Optional[PetriImage]:
        model = self._session.get(PetriImageModel, petri_image_id)
        return petri_image_to_entity(model) if model is not None else None

    def list_by_sample_id(self, sample_id: UUID) -> list[PetriImage]:
        statement = select(PetriImageModel).where(PetriImageModel.sample_id == sample_id)
        models = self._session.execute(statement).scalars().all()
        return [petri_image_to_entity(model) for model in models]
