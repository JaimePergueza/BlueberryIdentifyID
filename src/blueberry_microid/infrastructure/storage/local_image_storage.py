import uuid
from pathlib import Path

from blueberry_microid.application.exceptions import ImageStorageError
from blueberry_microid.application.ports.image_storage import ImageCategory, ImageStoragePort
from blueberry_microid.application.ports.image_validator import ALLOWED_EXTENSIONS


class LocalImageStorage(ImageStoragePort):
    """Filesystem-backed ImageStoragePort for local development.

    Petri and micro images are kept in physically separate directories.
    The final file name is always a fresh UUID — the caller-provided file
    name is only used (safely) to recover the extension, never to build the
    path, so it can never cause a collision or a path-traversal write.
    """

    def __init__(self, base_dir: Path) -> None:
        self._petri_dir = base_dir / "petri_images"
        self._micro_dir = base_dir / "micro_images"
        self._petri_dir.mkdir(parents=True, exist_ok=True)
        self._micro_dir.mkdir(parents=True, exist_ok=True)

    def save(self, *, category: ImageCategory, original_file_name: str, content: bytes) -> str:
        target_dir = self._petri_dir if category == ImageCategory.PETRI else self._micro_dir
        safe_name = f"{uuid.uuid4().hex}{self._safe_extension(original_file_name)}"
        target_path = target_dir / safe_name

        try:
            target_path.write_bytes(content)
        except OSError as exc:
            raise ImageStorageError(f"failed to write image to '{target_path}': {exc}") from exc

        return str(target_path)

    def delete(self, path: str) -> None:
        try:
            Path(path).unlink(missing_ok=True)
        except OSError as exc:
            raise ImageStorageError(f"failed to delete image at '{path}': {exc}") from exc

    @staticmethod
    def _safe_extension(original_file_name: str) -> str:
        extension = Path(original_file_name).suffix.lower()
        return extension if extension in ALLOWED_EXTENSIONS else ""
