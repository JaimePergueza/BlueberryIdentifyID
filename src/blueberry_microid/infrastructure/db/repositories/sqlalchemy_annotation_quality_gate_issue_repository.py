from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.annotation_quality_gate_issue_repository import (
    AnnotationQualityGateIssueRepositoryPort,
)
from blueberry_microid.domain.entities.annotation_quality_gate_issue import AnnotationQualityGateIssue
from blueberry_microid.infrastructure.db.models.annotation_quality_gate_issue import AnnotationQualityGateIssueModel
from blueberry_microid.infrastructure.db.repositories.mappers import annotation_quality_gate_issue_to_entity


class SqlAlchemyAnnotationQualityGateIssueRepository(AnnotationQualityGateIssueRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add_many(self, issues: list[AnnotationQualityGateIssue]) -> list[AnnotationQualityGateIssue]:
        models = [
            AnnotationQualityGateIssueModel(
                id=issue.id,
                quality_gate_run_id=issue.quality_gate_run_id,
                severity=issue.severity.value,
                code=issue.code,
                message=issue.message,
                split=issue.split,
                image_path=issue.image_path,
                annotation_ref=issue.annotation_ref,
                details=issue.details,
                created_at=issue.created_at,
            )
            for issue in issues
        ]
        self._session.add_all(models)
        self._commit_or_flush()
        for model in models:
            self._session.refresh(model)
        return [annotation_quality_gate_issue_to_entity(model) for model in models]

    def list_by_quality_gate_run_id(self, quality_gate_run_id: UUID) -> list[AnnotationQualityGateIssue]:
        statement = (
            select(AnnotationQualityGateIssueModel)
            .where(AnnotationQualityGateIssueModel.quality_gate_run_id == quality_gate_run_id)
            .order_by(
                AnnotationQualityGateIssueModel.severity.asc(),
                AnnotationQualityGateIssueModel.code.asc(),
                AnnotationQualityGateIssueModel.created_at.asc(),
                AnnotationQualityGateIssueModel.id.asc(),
            )
        )
        return [annotation_quality_gate_issue_to_entity(model) for model in self._session.execute(statement).scalars()]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
