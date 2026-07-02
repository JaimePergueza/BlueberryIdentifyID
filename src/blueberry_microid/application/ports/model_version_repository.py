from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.model_version import ModelVersion


class ModelVersionRepositoryPort(ABC):
    """Persistence contract for ModelVersion, independent of any ORM."""

    @abstractmethod
    def add(self, model_version: ModelVersion) -> ModelVersion:
        """Persist a new model version. Raises DuplicateModelVersionError if (name, version) exists."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, model_version_id: UUID) -> Optional[ModelVersion]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[ModelVersion]:
        raise NotImplementedError
