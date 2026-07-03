from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.training_preflight_issue_repository import (
    TrainingPreflightIssueRepositoryPort,
)
from blueberry_microid.domain.entities.training_preflight_issue import TrainingPreflightIssue
from blueberry_microid.infrastructure.db.models.training_preflight_issue import TrainingPreflightIssueModel
from blueberry_microid.infrastructure.db.repositories.mappers import training_preflight_issue_to_entity


class SqlAlchemyTrainingPreflightIssueRepository(TrainingPreflightIssueRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add_many(self, issues: list[TrainingPreflightIssue]) -> list[TrainingPreflightIssue]:
        models = [
            TrainingPreflightIssueModel(
                id=issue.id,
                preflight_run_id=issue.preflight_run_id,
                severity=issue.severity.value,
                code=issue.code,
                message=issue.message,
                field=issue.field,
                item_ref=issue.item_ref,
                created_at=issue.created_at,
            )
            for issue in issues
        ]
        self._session.add_all(models)
        self._commit_or_flush()
        for model in models:
            self._session.refresh(model)
        return [training_preflight_issue_to_entity(model) for model in models]

    def list_by_preflight_run_id(self, preflight_run_id: UUID) -> list[TrainingPreflightIssue]:
        statement = (
            select(TrainingPreflightIssueModel)
            .where(TrainingPreflightIssueModel.preflight_run_id == preflight_run_id)
            .order_by(TrainingPreflightIssueModel.created_at.asc(), TrainingPreflightIssueModel.id.asc())
        )
        models = self._session.execute(statement).scalars().all()
        return [training_preflight_issue_to_entity(model) for model in models]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
