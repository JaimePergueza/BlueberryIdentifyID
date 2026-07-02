import pytest

from blueberry_microid.application.exceptions import ImageTooLargeError, InvalidImageError
from blueberry_microid.application.ports.image_storage import ImageCategory
from blueberry_microid.application.services.image_intake_service import ImageIntakeService
from blueberry_microid.infrastructure.storage.pillow_image_validator import PillowImageValidator
from tests.unit.application.fakes import InMemoryImageStorage
from tests.unit.application.image_helpers import make_valid_jpeg_bytes


def test_validate_and_store_accepts_file_within_limit():
    content = make_valid_jpeg_bytes()
    service = ImageIntakeService(PillowImageValidator(), InMemoryImageStorage(), max_upload_size_bytes=len(content) + 1)

    result = service.validate_and_store(
        category=ImageCategory.PETRI,
        file_name="colony.jpg",
        mime_type="image/jpeg",
        declared_file_size_bytes=len(content),
        content=content,
    )

    assert result.file_size_bytes == len(content)


def test_validate_and_store_rejects_file_over_limit():
    content = make_valid_jpeg_bytes()
    storage = InMemoryImageStorage()
    service = ImageIntakeService(PillowImageValidator(), storage, max_upload_size_bytes=len(content) - 1)

    with pytest.raises(ImageTooLargeError):
        service.validate_and_store(
            category=ImageCategory.PETRI,
            file_name="colony.jpg",
            mime_type="image/jpeg",
            declared_file_size_bytes=len(content),
            content=content,
        )

    # Rejected before anything was written to storage.
    assert storage.saved == {}


def test_no_limit_means_any_size_is_allowed():
    content = make_valid_jpeg_bytes()
    service = ImageIntakeService(PillowImageValidator(), InMemoryImageStorage(), max_upload_size_bytes=None)

    result = service.validate_and_store(
        category=ImageCategory.PETRI,
        file_name="colony.jpg",
        mime_type="image/jpeg",
        declared_file_size_bytes=len(content),
        content=content,
    )

    assert result.file_size_bytes == len(content)


def test_size_limit_is_checked_before_size_mismatch():
    """If a file is both oversized and mismatched, the client should learn
    it's oversized — that's the more fundamental problem with the request.
    """
    content = make_valid_jpeg_bytes()
    service = ImageIntakeService(PillowImageValidator(), InMemoryImageStorage(), max_upload_size_bytes=len(content) - 1)

    with pytest.raises(ImageTooLargeError):
        service.validate_and_store(
            category=ImageCategory.PETRI,
            file_name="colony.jpg",
            mime_type="image/jpeg",
            declared_file_size_bytes=len(content) + 999,  # also mismatched
            content=content,
        )
