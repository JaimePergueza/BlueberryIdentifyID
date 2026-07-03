from uuid import UUID

from blueberry_microid.application.dto.image_audit_dto import ImageDatasetAuditRunDTO
from blueberry_microid.application.exceptions import ImageDatasetAuditRunNotFoundError
from blueberry_microid.application.ports.image_dataset_audit_issue_repository import (
    ImageDatasetAuditIssueRepositoryPort,
)
from blueberry_microid.application.ports.image_dataset_audit_run_repository import (
    ImageDatasetAuditRunRepositoryPort,
)


class GetImageDatasetAuditRunUseCase:
    def __init__(
        self,
        audit_run_repository: ImageDatasetAuditRunRepositoryPort,
        audit_issue_repository: ImageDatasetAuditIssueRepositoryPort,
    ) -> None:
        self._audit_run_repository = audit_run_repository
        self._audit_issue_repository = audit_issue_repository

    def execute(self, audit_run_id: UUID) -> ImageDatasetAuditRunDTO:
        audit_run = self._audit_run_repository.get_by_id(audit_run_id)
        if audit_run is None:
            raise ImageDatasetAuditRunNotFoundError(f"image_dataset_audit_run '{audit_run_id}' does not exist")
        issues = self._audit_issue_repository.list_by_audit_run_id(audit_run_id)
        return ImageDatasetAuditRunDTO.from_entity(audit_run, issues)
