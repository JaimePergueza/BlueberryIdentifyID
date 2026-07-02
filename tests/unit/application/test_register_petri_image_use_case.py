from uuid import uuid4

import pytest

from blueberry_microid.application.dto.petri_image_dto import RegisterPetriImageRequest
from blueberry_microid.application.exceptions import (
    ImageStorageCompensationError,
    InvalidImageError,
    SampleNotFoundError,
)
from blueberry_microid.application.services.image_intake_service import ImageIntakeService
from blueberry_microid.application.use_cases.petri_image.register_petri_image import RegisterPetriImageUseCase
from blueberry_microid.domain.entities.sample import Sample
from blueberry_microid.infrastructure.storage.pillow_image_validator import PillowImageValidator
from tests.unit.application.fakes import (
    FailingDeleteImageStorage,
    FailingPetriImageRepository,
    InMemoryImageStorage,
    InMemoryPetriImageRepository,
    InMemorySampleRepository,
)
from tests.unit.application.image_helpers import make_valid_jpeg_bytes


def _build_use_case(storage=None, petri_repository=None):
    sample_repository = InMemorySampleRepository()
    petri_repository = petri_repository or InMemoryPetriImageRepository()
    storage = storage or InMemoryImageStorage()
    intake = ImageIntakeService(PillowImageValidator(), storage)
    use_case = RegisterPetriImageUseCase(sample_repository, petri_repository, intake)
    return use_case, sample_repository, petri_repository, storage


def test_register_petri_image_with_valid_data():
    use_case, sample_repository, _, storage = _build_use_case()
    sample = sample_repository.add(Sample(sample_code="S-200"))
    content = make_valid_jpeg_bytes()

    dto = use_case.execute(
        RegisterPetriImageRequest(
            sample_id=sample.id,
            file_name="colony.jpg",
            mime_type="image/jpeg",
            file_size_bytes=len(content),
            content=content,
            culture_medium="PDA",
        )
    )

    assert dto.sample_id == sample.id
    assert dto.culture_medium == "PDA"
    assert dto.width is not None and dto.height is not None
    assert dto.file_size_bytes == len(content)
    assert dto.file_path in storage.saved


def test_register_petri_image_rejects_nonexistent_sample():
    use_case, *_ = _build_use_case()
    content = make_valid_jpeg_bytes()

    with pytest.raises(SampleNotFoundError):
        use_case.execute(
            RegisterPetriImageRequest(
                sample_id=uuid4(),
                file_name="colony.jpg",
                mime_type="image/jpeg",
                file_size_bytes=len(content),
                content=content,
            )
        )


def test_register_petri_image_rejects_empty_file():
    use_case, sample_repository, _, _ = _build_use_case()
    sample = sample_repository.add(Sample(sample_code="S-201"))

    with pytest.raises(InvalidImageError):
        use_case.execute(
            RegisterPetriImageRequest(
                sample_id=sample.id,
                file_name="colony.jpg",
                mime_type="image/jpeg",
                file_size_bytes=0,
                content=b"",
            )
        )


def test_register_petri_image_rejects_corrupted_image():
    use_case, sample_repository, _, _ = _build_use_case()
    sample = sample_repository.add(Sample(sample_code="S-202"))
    garbage = b"this-is-not-a-real-image-file"

    with pytest.raises(InvalidImageError):
        use_case.execute(
            RegisterPetriImageRequest(
                sample_id=sample.id,
                file_name="colony.jpg",
                mime_type="image/jpeg",
                file_size_bytes=len(garbage),
                content=garbage,
            )
        )


def test_register_petri_image_rejects_declared_size_mismatch():
    use_case, sample_repository, _, storage = _build_use_case()
    sample = sample_repository.add(Sample(sample_code="S-203"))
    content = make_valid_jpeg_bytes()

    with pytest.raises(InvalidImageError):
        use_case.execute(
            RegisterPetriImageRequest(
                sample_id=sample.id,
                file_name="colony.jpg",
                mime_type="image/jpeg",
                file_size_bytes=len(content) + 999,
                content=content,
            )
        )

    # The mismatch must be caught before anything is written to storage.
    assert storage.saved == {}


def test_register_petri_image_deletes_orphaned_file_when_repository_fails():
    use_case, sample_repository, _, storage = _build_use_case(petri_repository=FailingPetriImageRepository())
    sample = sample_repository.add(Sample(sample_code="S-204"))
    content = make_valid_jpeg_bytes()

    with pytest.raises(RuntimeError, match="simulated database failure"):
        use_case.execute(
            RegisterPetriImageRequest(
                sample_id=sample.id,
                file_name="colony.jpg",
                mime_type="image/jpeg",
                file_size_bytes=len(content),
                content=content,
            )
        )

    assert storage.saved == {}
    assert len(storage.deleted_paths) == 1


def test_register_petri_image_wraps_error_when_compensation_also_fails():
    use_case, sample_repository, _, _ = _build_use_case(
        storage=FailingDeleteImageStorage(), petri_repository=FailingPetriImageRepository()
    )
    sample = sample_repository.add(Sample(sample_code="S-205"))
    content = make_valid_jpeg_bytes()

    with pytest.raises(ImageStorageCompensationError) as exc_info:
        use_case.execute(
            RegisterPetriImageRequest(
                sample_id=sample.id,
                file_name="colony.jpg",
                mime_type="image/jpeg",
                file_size_bytes=len(content),
                content=content,
            )
        )

    # The original persistence failure must still be discoverable, not hidden.
    assert isinstance(exc_info.value.__cause__, RuntimeError)
    assert "simulated database failure" in str(exc_info.value.__cause__)
