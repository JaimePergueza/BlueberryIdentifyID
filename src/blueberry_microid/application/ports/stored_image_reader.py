from abc import ABC, abstractmethod


class StoredImageReaderPort(ABC):
    """Reads an image only after validating its persisted filesystem path."""

    @abstractmethod
    def read(self, file_path: str) -> bytes:
        raise NotImplementedError
