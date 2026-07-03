from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.image_dataset_audit_issue_repository import (
    ImageDatasetAuditIssueRepositoryPort,
)
from blueberry_microid.domain.entities.image_dataset_audit_issue import ImageDatasetAuditIssue
from blueberry_microid.infrastructure.db.models.image_dataset_audit_issue import ImageDatasetAuditIssueModel
from blueberry_microid.infrastructure.db.repositories.mappers import image_dataset_audit_issue_to_entity


class SqlAlchemyImageDatasetAuditIssueRepository(ImageDatasetAuditIssueRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add_many(self, issues: list[ImageDatasetAuditIssue]) -> list[ImageDatasetAuditIssue]:
        models = [
            ImageDatasetAuditIssueModel(
                id=issue.id,
                audit_run_id=issue.audit_run_id,
                severity=issue.severity.value,
                modality=issue.modality.value,
                dataset_item_id=issue.dataset_item_id,
                dataset_split_item_id=issue.dataset_split_item_id,
                image_path=issue.image_path,
                code=issue.code,
                message=issue.message,
                details=issue.details,
                created_at=issue.created_at,
            )
            for issue in issues
        ]
        self._session.add_all(models)
        self._commit_or_flush()
        for model in models:
            self._session.refresh(model)
        return [image_dataset_audit_issue_to_entity(model) for model in models]

    def list_by_audit_run_id(self, audit_run_id: UUID) -> list[ImageDatasetAuditIssue]:
        statement = (
            select(ImageDatasetAuditIssueModel)
            .where(ImageDatasetAuditIssueModel.audit_run_id == audit_run_id)
            .order_by(ImageDatasetAuditIssueModel.created_at.asc(), ImageDatasetAuditIssueModel.id.asc())
        )
        models = self._session.execute(statement).scalars().all()
        return [image_dataset_audit_issue_to_entity(model) for model in models]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
