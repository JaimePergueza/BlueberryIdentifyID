from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from blueberry_microid.application.exceptions import InvalidImageError
from blueberry_microid.application.ports.image_validator import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    EXTENSION_TO_PILLOW_FORMAT,
    MIME_TYPE_TO_PILLOW_FORMAT,
    ImageValidationResult,
    ImageValidatorPort,
)


class PillowImageValidator(ImageValidatorPort):
    """Validates image uploads using Pillow.

    Checks, in order: non-empty content, allowed MIME type, allowed file
    extension, that Pillow can actually decode the bytes as an intact image
    (rejecting corrupted files), and — because a client's declared MIME type
    and file name are just claims, not proof — that the format Pillow
    actually detected agrees with both of them. A `.png`-named file that is
    really a JPEG, or a request declaring `image/png` for JPEG bytes, is
    rejected even though each individual check (extension allowed, MIME
    allowed, decodes fine) would pass on its own.
    """

    def validate(self, *, file_name: str, mime_type: str, content: bytes) -> ImageValidationResult:
        if len(content) == 0:
            raise InvalidImageError("uploaded file is empty")

        if mime_type not in ALLOWED_MIME_TYPES:
            allowed = ", ".join(sorted(ALLOWED_MIME_TYPES))
            raise InvalidImageError(f"mime type '{mime_type}' is not allowed; expected one of: {allowed}")

        extension = Path(file_name).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
            raise InvalidImageError(f"file extension '{extension}' is not allowed; expected one of: {allowed}")

        try:
            with Image.open(BytesIO(content)) as probe:
                probe.verify()
        except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
            raise InvalidImageError(f"file is not a valid or is a corrupted image: {exc}") from exc

        # Image.verify() leaves the file object unusable for further reads,
        # so dimensions/format must come from a fresh decode.
        try:
            with Image.open(BytesIO(content)) as image:
                width, height = image.size
                actual_format = image.format
        except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
            raise InvalidImageError(f"could not read image dimensions: {exc}") from exc

        expected_format_for_mime = MIME_TYPE_TO_PILLOW_FORMAT[mime_type]
        if actual_format != expected_format_for_mime:
            raise InvalidImageError(
                f"declared mime type '{mime_type}' does not match the actual image format "
                f"detected by Pillow ('{actual_format}')"
            )

        expected_format_for_extension = EXTENSION_TO_PILLOW_FORMAT[extension]
        if actual_format != expected_format_for_extension:
            raise InvalidImageError(
                f"file extension '{extension}' does not match the actual image format "
                f"detected by Pillow ('{actual_format}')"
            )

        return ImageValidationResult(width=width, height=height)
