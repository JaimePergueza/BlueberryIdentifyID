"""Upload-specific image storage backed by the local filesystem.

Identical to ``LocalImageStorage`` in behaviour but rooted at the configured
``upload_storage_dir`` (env: ``BLUEBERRY_MICROID_UPLOAD_STORAGE_DIR``) so
that ad-hoc uploads from the two-image upload endpoint are physically
separated from the registered ``PetriImage``/``MicroImage`` storage used by
the main workflow.
"""

import uuid
from pathlib import Path

from blueberry_microid.application.exceptions import ImageStorageError
from blueberry_microid.application.ports.image_storage import ImageCategory, ImageStoragePort
from blueberry_microid.application.ports.image_validator import ALLOWED_EXTENSIONS


class LocalUploadStorage(ImageStoragePort):
    """Filesystem-backed storage for the two-image upload endpoint.

    Petri and micro uploads are kept in physically separate subdirectories
    (``petri/`` and ``micro/``) under ``upload_dir``.  The final file name is
    always a fresh UUID so the caller-provided name can never cause a
    collision or path-traversal write.
    """

    def __init__(self, upload_dir: Path) -> None:
        self._petri_dir = upload_dir / "petri"
        self._micro_dir = upload_dir / "micro"
        self._petri_dir.mkdir(parents=True, exist_ok=True)
        self._micro_dir.mkdir(parents=True, exist_ok=True)

    def save(self, *, category: ImageCategory, original_file_name: str, content: bytes) -> str:
        target_dir = self._petri_dir if category == ImageCategory.PETRI else self._micro_dir
        safe_name = f"{uuid.uuid4().hex}{self._safe_extension(original_file_name)}"
        target_path = target_dir / safe_name
        try:
            target_path.write_bytes(content)
        except OSError as exc:
            raise ImageStorageError(f"failed to write upload to '{target_path}': {exc}") from exc
        return str(target_path)

    def delete(self, path: str) -> None:
        try:
            Path(path).unlink(missing_ok=True)
        except OSError as exc:
            raise ImageStorageError(f"failed to delete upload at '{path}': {exc}") from exc

    @staticmethod
    def _safe_extension(original_file_name: str) -> str:
        ext = Path(original_file_name).suffix.lower()
        return ext if ext in ALLOWED_EXTENSIONS else ""
