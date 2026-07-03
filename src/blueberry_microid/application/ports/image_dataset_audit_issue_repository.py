from abc import ABC, abstractmethod
from uuid import UUID

from blueberry_microid.domain.entities.image_dataset_audit_issue import ImageDatasetAuditIssue


class ImageDatasetAuditIssueRepositoryPort(ABC):
    @abstractmethod
    def add_many(self, issues: list[ImageDatasetAuditIssue]) -> list[ImageDatasetAuditIssue]:
        raise NotImplementedError

    @abstractmethod
    def list_by_audit_run_id(self, audit_run_id: UUID) -> list[ImageDatasetAuditIssue]:
        raise NotImplementedError
