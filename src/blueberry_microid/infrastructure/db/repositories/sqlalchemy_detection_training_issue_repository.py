from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.detection_training_issue_repository import (
    DetectionTrainingIssueRepositoryPort,
)
from blueberry_microid.domain.entities.detection_training_issue import DetectionTrainingIssue
from blueberry_microid.infrastructure.db.models.detection_training_issue import DetectionTrainingIssueModel
from blueberry_microid.infrastructure.db.repositories.mappers import detection_training_issue_to_entity


class SqlAlchemyDetectionTrainingIssueRepository(DetectionTrainingIssueRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add_many(self, issues: list[DetectionTrainingIssue]) -> list[DetectionTrainingIssue]:
        models = [
            DetectionTrainingIssueModel(
                id=issue.id,
                detection_training_run_id=issue.detection_training_run_id,
                severity=issue.severity.value,
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
        return [detection_training_issue_to_entity(model) for model in models]

    def list_by_detection_training_run_id(self, detection_training_run_id: UUID) -> list[DetectionTrainingIssue]:
        statement = (
            select(DetectionTrainingIssueModel)
            .where(DetectionTrainingIssueModel.detection_training_run_id == detection_training_run_id)
            .order_by(
                DetectionTrainingIssueModel.severity.asc(),
                DetectionTrainingIssueModel.code.asc(),
                DetectionTrainingIssueModel.created_at.asc(),
                DetectionTrainingIssueModel.id.asc(),
            )
        )
        return [detection_training_issue_to_entity(model) for model in self._session.execute(statement).scalars()]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
