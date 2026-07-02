from blueberry_microid.application.dto.sample_dto import CreateSampleRequest, SampleDTO
from blueberry_microid.application.exceptions import DuplicateSampleCodeError
from blueberry_microid.application.ports.sample_repository import SampleRepositoryPort
from blueberry_microid.domain.entities.sample import Sample
from blueberry_microid.domain.value_objects.sample_code import SampleCode


class CreateSampleUseCase:
    """Registers a new blueberry sample.

    `product` is not part of the request: this system supports blueberry
    only, and `Sample` enforces that invariant on construction.
    """

    def __init__(self, sample_repository: SampleRepositoryPort) -> None:
        self._sample_repository = sample_repository

    def execute(self, request: CreateSampleRequest) -> SampleDTO:
        normalized_code = str(SampleCode(request.sample_code))
        if self._sample_repository.get_by_sample_code(normalized_code) is not None:
            raise DuplicateSampleCodeError(f"sample_code '{normalized_code}' already exists")

        sample = Sample(
            sample_code=normalized_code,
            lot_code=request.lot_code,
            origin=request.origin,
            collection_date=request.collection_date,
            notes=request.notes,
        )
        created = self._sample_repository.add(sample)
        return SampleDTO.from_entity(created)
