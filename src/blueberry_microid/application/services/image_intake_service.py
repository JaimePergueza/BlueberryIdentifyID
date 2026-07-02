from dataclasses import dataclass
from typing import Optional

from blueberry_microid.application.exceptions import ImageTooLargeError, InvalidImageError
from blueberry_microid.application.ports.image_storage import ImageCategory, ImageStoragePort
from blueberry_microid.application.ports.image_validator import ImageValidatorPort


@dataclass(frozen=True, slots=True)
class StoredImageIntake:
    """Result of validating and storing one image upload."""

    file_path: str
    file_size_bytes: int
    width: Optional[int]
    height: Optional[int]


class ImageIntakeService:
    """Shared validate-then-store flow used by RegisterPetriImageUseCase and
    RegisterMicroImageUseCase.

    The caller-declared `declared_file_size_bytes` is never trusted blindly:
    it must match the actual byte count of `content`, or the upload is
    rejected outright. The size persisted downstream is always the value
    computed here from the real bytes, never the caller's claim.

    `max_upload_size_bytes` (sourced from `Settings.max_upload_size_mb`, never
    hardcoded here or in a router) is enforced against that same real byte
    count before anything is validated or written to storage. `None` means
    no limit — used by tests that don't care about it.

    Also owns `cleanup()` so use cases can undo a successful `save()` if the
    repository write that follows it fails, without depending on
    `ImageStoragePort` directly.
    """

    def __init__(
        self,
        image_validator: ImageValidatorPort,
        image_storage: ImageStoragePort,
        max_upload_size_bytes: Optional[int] = None,
    ) -> None:
        self._image_validator = image_validator
        self._image_storage = image_storage
        self._max_upload_size_bytes = max_upload_size_bytes

    def validate_and_store(
        self,
        *,
        category: ImageCategory,
        file_name: str,
        mime_type: str,
        declared_file_size_bytes: int,
        content: bytes,
    ) -> StoredImageIntake:
        actual_size = len(content)

        if self._max_upload_size_bytes is not None and actual_size > self._max_upload_size_bytes:
            raise ImageTooLargeError(
                f"uploaded file is {actual_size} bytes, which exceeds the maximum allowed "
                f"size of {self._max_upload_size_bytes} bytes"
            )

        if actual_size != declared_file_size_bytes:
            raise InvalidImageError(
                f"declared file_size_bytes ({declared_file_size_bytes}) does not match "
                f"the actual content size ({actual_size})"
            )

        validation = self._image_validator.validate(file_name=file_name, mime_type=mime_type, content=content)
        file_path = self._image_storage.save(category=category, original_file_name=file_name, content=content)

        return StoredImageIntake(
            file_path=file_path,
            file_size_bytes=actual_size,
            width=validation.width,
            height=validation.height,
        )

    def cleanup(self, file_path: str) -> None:
        self._image_storage.delete(file_path)
