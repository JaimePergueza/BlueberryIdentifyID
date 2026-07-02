from abc import ABC, abstractmethod
from enum import Enum


class ImageCategory(str, Enum):
    """Which physically separate storage area an image belongs to.

    PETRI images and MICRO images are never mixed in the same directory,
    mirroring the fact that they are different evidence types for the same
    Sample (see CLAUDE.md, "separacion macro/micro").
    """

    PETRI = "petri"
    MICRO = "micro"


class ImageStoragePort(ABC):
    """Persists raw image bytes to a storage backend and returns where they landed.

    Implementations must never trust the caller-provided file name for the
    final path (collision/traversal risk) — see LocalImageStorage.
    """

    @abstractmethod
    def save(self, *, category: ImageCategory, original_file_name: str, content: bytes) -> str:
        """Persist `content` and return the final storage path/identifier."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, path: str) -> None:
        """Remove a previously stored image.

        Must be idempotent: deleting a path that no longer exists is not an
        error (the desired end state — "no file at this path" — already
        holds). Only a genuine I/O failure should raise.
        """
        raise NotImplementedError
