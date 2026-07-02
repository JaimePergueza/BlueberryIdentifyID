from uuid import UUID

from blueberry_microid.application.dto.sample_dto import SampleDTO
from blueberry_microid.application.exceptions import SampleNotFoundError
from blueberry_microid.application.ports.sample_repository import SampleRepositoryPort


class GetSampleByIdUseCase:
    """Reads a single Sample by its UUID."""

    def __init__(self, sample_repository: SampleRepositoryPort) -> None:
        self._sample_repository = sample_repository

    def execute(self, sample_id: UUID) -> SampleDTO:
        sample = self._sample_repository.get_by_id(sample_id)
        if sample is None:
            raise SampleNotFoundError(f"sample '{sample_id}' does not exist")
        return SampleDTO.from_entity(sample)


class GetSampleBySampleCodeUseCase:
    """Reads a single Sample by its human-assigned sample_code."""

    def __init__(self, sample_repository: SampleRepositoryPort) -> None:
        self._sample_repository = sample_repository

    def execute(self, sample_code: str) -> SampleDTO:
        sample = self._sample_repository.get_by_sample_code(sample_code)
        if sample is None:
            raise SampleNotFoundError(f"sample with sample_code '{sample_code}' does not exist")
        return SampleDTO.from_entity(sample)
