from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.detection_training_environment_issue_repository import (
    DetectionTrainingEnvironmentIssueRepositoryPort,
)
from blueberry_microid.domain.entities.detection_training_environment_issue import (
    DetectionTrainingEnvironmentIssue,
)
from blueberry_microid.infrastructure.db.models.detection_training_environment_issue import (
    DetectionTrainingEnvironmentIssueModel,
)
from blueberry_microid.infrastructure.db.repositories.mappers import detection_training_environment_issue_to_entity


class SqlAlchemyDetectionTrainingEnvironmentIssueRepository(DetectionTrainingEnvironmentIssueRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add_many(
        self, issues: list[DetectionTrainingEnvironmentIssue]
    ) -> list[DetectionTrainingEnvironmentIssue]:
        models = [
            DetectionTrainingEnvironmentIssueModel(
                id=issue.id,
                environment_spec_id=issue.environment_spec_id,
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
        return [detection_training_environment_issue_to_entity(model) for model in models]

    def list_by_environment_spec_id(self, environment_spec_id: UUID) -> list[DetectionTrainingEnvironmentIssue]:
        statement = (
            select(DetectionTrainingEnvironmentIssueModel)
            .where(DetectionTrainingEnvironmentIssueModel.environment_spec_id == environment_spec_id)
            .order_by(
                DetectionTrainingEnvironmentIssueModel.severity.asc(),
                DetectionTrainingEnvironmentIssueModel.code.asc(),
                DetectionTrainingEnvironmentIssueModel.created_at.asc(),
                DetectionTrainingEnvironmentIssueModel.id.asc(),
            )
        )
        return [
            detection_training_environment_issue_to_entity(model)
            for model in self._session.execute(statement).scalars()
        ]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
