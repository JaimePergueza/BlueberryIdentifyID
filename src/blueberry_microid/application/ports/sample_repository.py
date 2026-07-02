from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.sample import Sample


class SampleRepositoryPort(ABC):
    """Persistence contract for Sample, independent of any ORM."""

    @abstractmethod
    def add(self, sample: Sample) -> Sample:
        """Persist a new sample. Raises DuplicateSampleCodeError if sample_code exists."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, sample_id: UUID) -> Optional[Sample]:
        raise NotImplementedError

    @abstractmethod
    def get_by_sample_code(self, sample_code: str) -> Optional[Sample]:
        raise NotImplementedError
