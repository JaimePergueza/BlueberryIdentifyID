from pathlib import Path

from blueberry_microid.application.ports.stored_image_reader import StoredImageReaderPort
from blueberry_microid.application.stored_image_exceptions import StoredImageUnavailableError


class LocalStoredImageReader(StoredImageReaderPort):
    """Filesystem reader restricted to explicitly approved storage roots."""

    def __init__(self, allowed_roots: tuple[Path, ...]) -> None:
        if not allowed_roots:
            raise ValueError("at least one allowed storage root is required")
        self._allowed_roots = tuple(root.resolve() for root in allowed_roots)

    def read(self, file_path: str) -> bytes:
        try:
            candidate = Path(file_path).resolve(strict=False)
        except (OSError, RuntimeError, ValueError) as exc:
            raise StoredImageUnavailableError("Stored image content is unavailable") from exc

        if not any(candidate.is_relative_to(root) for root in self._allowed_roots):
            raise StoredImageUnavailableError("Stored image content is unavailable")
        if not candidate.is_file():
            raise StoredImageUnavailableError("Stored image content is unavailable")

        try:
            return candidate.read_bytes()
        except OSError as exc:
            raise StoredImageUnavailableError("Stored image content is unavailable") from exc
