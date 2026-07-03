from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.image_dataset_audit_run import ImageDatasetAuditRun


class ImageDatasetAuditRunRepositoryPort(ABC):
    @abstractmethod
    def add(self, audit_run: ImageDatasetAuditRun) -> ImageDatasetAuditRun:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, audit_run_id: UUID) -> Optional[ImageDatasetAuditRun]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[ImageDatasetAuditRun]:
        raise NotImplementedError

    @abstractmethod
    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[ImageDatasetAuditRun]:
        raise NotImplementedError
