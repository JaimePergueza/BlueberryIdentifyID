from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.micro_image import MicroImage


class MicroImageRepositoryPort(ABC):
    """Persistence contract for MicroImage, independent of any ORM."""

    @abstractmethod
    def add(self, micro_image: MicroImage) -> MicroImage:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, micro_image_id: UUID) -> Optional[MicroImage]:
        raise NotImplementedError

    @abstractmethod
    def list_by_sample_id(self, sample_id: UUID) -> list[MicroImage]:
        raise NotImplementedError
