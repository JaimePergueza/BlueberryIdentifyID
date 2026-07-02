from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.petri_image import PetriImage


class PetriImageRepositoryPort(ABC):
    """Persistence contract for PetriImage, independent of any ORM."""

    @abstractmethod
    def add(self, petri_image: PetriImage) -> PetriImage:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, petri_image_id: UUID) -> Optional[PetriImage]:
        raise NotImplementedError

    @abstractmethod
    def list_by_sample_id(self, sample_id: UUID) -> list[PetriImage]:
        raise NotImplementedError
