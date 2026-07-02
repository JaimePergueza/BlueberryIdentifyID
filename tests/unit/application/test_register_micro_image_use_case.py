import pytest

from blueberry_microid.application.dto.micro_image_dto import RegisterMicroImageRequest
from blueberry_microid.application.exceptions import InvalidImageError
from blueberry_microid.application.services.image_intake_service import ImageIntakeService
from blueberry_microid.application.use_cases.micro_image.register_micro_image import RegisterMicroImageUseCase
from blueberry_microid.domain.entities.sample import Sample
from blueberry_microid.infrastructure.storage.pillow_image_validator import PillowImageValidator
from tests.unit.application.fakes import (
    FailingMicroImageRepository,
    InMemoryImageStorage,
    InMemoryMicroImageRepository,
    InMemorySampleRepository,
)
from tests.unit.application.image_helpers import make_valid_jpeg_bytes


def _build_use_case(storage=None, micro_repository=None):
    sample_repository = InMemorySampleRepository()
    micro_repository = micro_repository or InMemoryMicroImageRepository()
    storage = storage or InMemoryImageStorage()
    intake = ImageIntakeService(PillowImageValidator(), storage)
    use_case = RegisterMicroImageUseCase(sample_repository, micro_repository, intake)
    return use_case, sample_repository, micro_repository, storage


def test_register_micro_image_with_valid_data():
    use_case, sample_repository, _, _ = _build_use_case()
    sample = sample_repository.add(Sample(sample_code="S-300"))
    content = make_valid_jpeg_bytes()

    dto = use_case.execute(
        RegisterMicroImageRequest(
            sample_id=sample.id,
            file_name="hyphae.jpg",
            mime_type="image/jpeg",
            file_size_bytes=len(content),
            content=content,
            magnification="400x",
        )
    )

    assert dto.sample_id == sample.id
    assert dto.magnification == "400x"
    assert dto.width is not None and dto.height is not None
    assert dto.file_size_bytes == len(content)


def test_register_micro_image_rejects_invalid_mime_type():
    use_case, sample_repository, _, _ = _build_use_case()
    sample = sample_repository.add(Sample(sample_code="S-301"))
    content = make_valid_jpeg_bytes()

    with pytest.raises(InvalidImageError):
        use_case.execute(
            RegisterMicroImageRequest(
                sample_id=sample.id,
                file_name="hyphae.jpg",
                mime_type="application/pdf",
                file_size_bytes=len(content),
                content=content,
            )
        )


def test_register_micro_image_rejects_declared_size_mismatch():
    use_case, sample_repository, _, storage = _build_use_case()
    sample = sample_repository.add(Sample(sample_code="S-302"))
    content = make_valid_jpeg_bytes()

    with pytest.raises(InvalidImageError):
        use_case.execute(
            RegisterMicroImageRequest(
                sample_id=sample.id,
                file_name="hyphae.jpg",
                mime_type="image/jpeg",
                file_size_bytes=len(content) - 1,
                content=content,
            )
        )

    assert storage.saved == {}


def test_register_micro_image_deletes_orphaned_file_when_repository_fails():
    use_case, sample_repository, _, storage = _build_use_case(micro_repository=FailingMicroImageRepository())
    sample = sample_repository.add(Sample(sample_code="S-303"))
    content = make_valid_jpeg_bytes()

    with pytest.raises(RuntimeError, match="simulated database failure"):
        use_case.execute(
            RegisterMicroImageRequest(
                sample_id=sample.id,
                file_name="hyphae.jpg",
                mime_type="image/jpeg",
                file_size_bytes=len(content),
                content=content,
            )
        )

    assert storage.saved == {}
    assert len(storage.deleted_paths) == 1
