from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

# Single source of truth for allowed image formats, shared by the validator
# implementation and the local storage implementation (safe extension check).
ALLOWED_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/tiff"})
ALLOWED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".tif", ".tiff"})

# Both `UploadFile.content_type` and the client-supplied file name are
# caller-declared metadata — nothing stops a client from naming a JPEG file
# "colony.png" or declaring `mime_type=image/png` for JPEG bytes. These maps
# let the validator check what Pillow *actually* decoded against what was
# claimed, for both the MIME type and the extension.
MIME_TYPE_TO_PILLOW_FORMAT = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/tiff": "TIFF",
}
EXTENSION_TO_PILLOW_FORMAT = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".tif": "TIFF",
    ".tiff": "TIFF",
}


@dataclass(frozen=True, slots=True)
class ImageValidationResult:
    """Facts established about an image once it has passed validation."""

    width: Optional[int] = None
    height: Optional[int] = None


class ImageValidatorPort(ABC):
    """Validates raw image bytes before they are stored or persisted.

    Implementations must raise `application.exceptions.InvalidImageError`
    (not a bare exception) for any rejection: empty file, disallowed MIME
    type, disallowed extension, or a corrupted/unreadable image.
    """

    @abstractmethod
    def validate(self, *, file_name: str, mime_type: str, content: bytes) -> ImageValidationResult:
        raise NotImplementedError
