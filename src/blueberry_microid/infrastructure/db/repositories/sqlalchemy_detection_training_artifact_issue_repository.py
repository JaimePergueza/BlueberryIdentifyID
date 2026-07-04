from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.detection_training_artifact_issue_repository import (
    DetectionTrainingArtifactIssueRepositoryPort,
)
from blueberry_microid.domain.entities.detection_training_artifact_issue import DetectionTrainingArtifactIssue
from blueberry_microid.infrastructure.db.models.detection_training_artifact_issue import (
    DetectionTrainingArtifactIssueModel,
)
from blueberry_microid.infrastructure.db.repositories.mappers import detection_training_artifact_issue_to_entity


class SqlAlchemyDetectionTrainingArtifactIssueRepository(DetectionTrainingArtifactIssueRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add_many(self, issues: list[DetectionTrainingArtifactIssue]) -> list[DetectionTrainingArtifactIssue]:
        models = [
            DetectionTrainingArtifactIssueModel(
                id=issue.id,
                artifact_policy_id=issue.artifact_policy_id,
                severity=issue.severity.value,
                code=issue.code,
                message=issue.message,
                artifact_path=issue.artifact_path,
                details=issue.details,
                created_at=issue.created_at,
            )
            for issue in issues
        ]
        self._session.add_all(models)
        self._commit_or_flush()
        for model in models:
            self._session.refresh(model)
        return [detection_training_artifact_issue_to_entity(model) for model in models]

    def list_by_artifact_policy_id(self, artifact_policy_id: UUID) -> list[DetectionTrainingArtifactIssue]:
        statement = (
            select(DetectionTrainingArtifactIssueModel)
            .where(DetectionTrainingArtifactIssueModel.artifact_policy_id == artifact_policy_id)
            .order_by(
                DetectionTrainingArtifactIssueModel.severity.asc(),
                DetectionTrainingArtifactIssueModel.code.asc(),
                DetectionTrainingArtifactIssueModel.created_at.asc(),
                DetectionTrainingArtifactIssueModel.id.asc(),
            )
        )
        return [
            detection_training_artifact_issue_to_entity(model)
            for model in self._session.execute(statement).scalars()
        ]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
