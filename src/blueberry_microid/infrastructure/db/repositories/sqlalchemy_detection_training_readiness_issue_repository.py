from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.detection_training_readiness_issue_repository import (
    DetectionTrainingReadinessIssueRepositoryPort,
)
from blueberry_microid.domain.entities.detection_training_readiness_issue import (
    DetectionTrainingReadinessIssue,
)
from blueberry_microid.infrastructure.db.models.detection_training_readiness_issue import (
    DetectionTrainingReadinessIssueModel,
)
from blueberry_microid.infrastructure.db.repositories.mappers import detection_training_readiness_issue_to_entity


class SqlAlchemyDetectionTrainingReadinessIssueRepository(DetectionTrainingReadinessIssueRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add_many(
        self, issues: list[DetectionTrainingReadinessIssue]
    ) -> list[DetectionTrainingReadinessIssue]:
        models = [
            DetectionTrainingReadinessIssueModel(
                id=issue.id,
                readiness_report_id=issue.readiness_report_id,
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
        return [detection_training_readiness_issue_to_entity(model) for model in models]

    def list_by_readiness_report_id(self, readiness_report_id: UUID) -> list[DetectionTrainingReadinessIssue]:
        statement = (
            select(DetectionTrainingReadinessIssueModel)
            .where(DetectionTrainingReadinessIssueModel.readiness_report_id == readiness_report_id)
            .order_by(
                DetectionTrainingReadinessIssueModel.severity.asc(),
                DetectionTrainingReadinessIssueModel.code.asc(),
                DetectionTrainingReadinessIssueModel.created_at.asc(),
                DetectionTrainingReadinessIssueModel.id.asc(),
            )
        )
        return [
            detection_training_readiness_issue_to_entity(model)
            for model in self._session.execute(statement).scalars()
        ]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
