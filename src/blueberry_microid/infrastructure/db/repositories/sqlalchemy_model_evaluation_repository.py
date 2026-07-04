from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.model_evaluation_repository import (
    ModelCandidateRepositoryPort,
    ModelEvaluationIssueRepositoryPort,
    ModelEvaluationRunRepositoryPort,
    ModelPromotionGateRunRepositoryPort,
)
from blueberry_microid.domain.entities.model_candidate import ModelCandidate
from blueberry_microid.domain.entities.model_evaluation_issue import ModelEvaluationIssue
from blueberry_microid.domain.entities.model_evaluation_run import ModelEvaluationRun
from blueberry_microid.domain.entities.model_promotion_gate_run import ModelPromotionGateRun
from blueberry_microid.infrastructure.db.models.model_candidate import ModelCandidateModel
from blueberry_microid.infrastructure.db.models.model_evaluation_issue import ModelEvaluationIssueModel
from blueberry_microid.infrastructure.db.models.model_evaluation_run import ModelEvaluationRunModel
from blueberry_microid.infrastructure.db.models.model_promotion_gate_run import ModelPromotionGateRunModel


def _candidate_to_entity(model: ModelCandidateModel) -> ModelCandidate:
    return ModelCandidate(
        id=model.id,
        local_yolo_training_execution_run_id=model.local_yolo_training_execution_run_id,
        detection_training_run_id=model.detection_training_run_id,
        model_version_id=model.model_version_id,
        candidate_kind=model.candidate_kind,
        status=model.status,
        model_artifact_path=model.model_artifact_path,
        model_artifact_checksum_sha256=model.model_artifact_checksum_sha256,
        model_artifact_size_bytes=model.model_artifact_size_bytes,
        metrics_artifact_path=model.metrics_artifact_path,
        config_artifact_path=model.config_artifact_path,
        source_summary=model.source_summary or {},
        created_at=model.created_at,
        created_by=model.created_by,
        notes=model.notes,
    )


def _evaluation_to_entity(model: ModelEvaluationRunModel) -> ModelEvaluationRun:
    return ModelEvaluationRun(
        id=model.id,
        model_candidate_id=model.model_candidate_id,
        local_yolo_training_execution_run_id=model.local_yolo_training_execution_run_id,
        status=model.status,
        decision=model.decision,
        metrics_summary=model.metrics_summary or {},
        thresholds=model.thresholds or {},
        dataset_summary=model.dataset_summary or {},
        artifact_summary=model.artifact_summary or {},
        evaluation_summary=model.evaluation_summary or {},
        started_at=model.started_at,
        completed_at=model.completed_at,
        created_at=model.created_at,
        error_message=model.error_message,
        warning_count=model.warning_count,
        error_count=model.error_count,
        info_count=model.info_count,
    )


def _issue_to_entity(model: ModelEvaluationIssueModel) -> ModelEvaluationIssue:
    return ModelEvaluationIssue(
        id=model.id,
        model_evaluation_run_id=model.model_evaluation_run_id,
        severity=model.severity,
        code=model.code,
        message=model.message,
        details=model.details,
        created_at=model.created_at,
    )


def _gate_to_entity(model: ModelPromotionGateRunModel) -> ModelPromotionGateRun:
    return ModelPromotionGateRun(
        id=model.id,
        model_candidate_id=model.model_candidate_id,
        model_evaluation_run_id=model.model_evaluation_run_id,
        decision=model.decision,
        gate_summary=model.gate_summary or {},
        blocking_reasons=model.blocking_reasons or [],
        required_thresholds=model.required_thresholds or {},
        observed_metrics=model.observed_metrics or {},
        created_at=model.created_at,
        created_by=model.created_by,
        notes=model.notes,
    )


class SqlAlchemyModelCandidateRepository(ModelCandidateRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add(self, candidate: ModelCandidate) -> ModelCandidate:
        model = ModelCandidateModel(
            id=candidate.id,
            local_yolo_training_execution_run_id=candidate.local_yolo_training_execution_run_id,
            detection_training_run_id=candidate.detection_training_run_id,
            model_version_id=candidate.model_version_id,
            candidate_kind=candidate.candidate_kind.value,
            status=candidate.status.value,
            model_artifact_path=candidate.model_artifact_path,
            model_artifact_checksum_sha256=candidate.model_artifact_checksum_sha256,
            model_artifact_size_bytes=candidate.model_artifact_size_bytes,
            metrics_artifact_path=candidate.metrics_artifact_path,
            config_artifact_path=candidate.config_artifact_path,
            source_summary=candidate.source_summary,
            created_at=candidate.created_at,
            created_by=candidate.created_by,
            notes=candidate.notes,
        )
        self._session.add(model)
        self._commit_or_flush()
        self._session.refresh(model)
        return _candidate_to_entity(model)

    def get_by_id(self, candidate_id: UUID) -> ModelCandidate | None:
        model = self._session.get(ModelCandidateModel, candidate_id)
        return _candidate_to_entity(model) if model else None

    def list_all(self) -> list[ModelCandidate]:
        statement = select(ModelCandidateModel).order_by(ModelCandidateModel.created_at.asc(), ModelCandidateModel.id.asc())
        return [_candidate_to_entity(model) for model in self._session.execute(statement).scalars()]

    def _commit_or_flush(self) -> None:
        self._session.commit() if self._auto_commit else self._session.flush()


class SqlAlchemyModelEvaluationRunRepository(ModelEvaluationRunRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add(self, run: ModelEvaluationRun) -> ModelEvaluationRun:
        model = ModelEvaluationRunModel(
            id=run.id,
            model_candidate_id=run.model_candidate_id,
            local_yolo_training_execution_run_id=run.local_yolo_training_execution_run_id,
            status=run.status.value,
            decision=run.decision.value,
            metrics_summary=run.metrics_summary,
            thresholds=run.thresholds,
            dataset_summary=run.dataset_summary,
            artifact_summary=run.artifact_summary,
            evaluation_summary=run.evaluation_summary,
            started_at=run.started_at,
            completed_at=run.completed_at,
            created_at=run.created_at,
            error_message=run.error_message,
            warning_count=run.warning_count,
            error_count=run.error_count,
            info_count=run.info_count,
        )
        self._session.add(model)
        self._commit_or_flush()
        self._session.refresh(model)
        return _evaluation_to_entity(model)

    def get_by_id(self, run_id: UUID) -> ModelEvaluationRun | None:
        model = self._session.get(ModelEvaluationRunModel, run_id)
        return _evaluation_to_entity(model) if model else None

    def list_by_model_candidate_id(self, candidate_id: UUID) -> list[ModelEvaluationRun]:
        statement = (
            select(ModelEvaluationRunModel)
            .where(ModelEvaluationRunModel.model_candidate_id == candidate_id)
            .order_by(ModelEvaluationRunModel.created_at.asc(), ModelEvaluationRunModel.id.asc())
        )
        return [_evaluation_to_entity(model) for model in self._session.execute(statement).scalars()]

    def _commit_or_flush(self) -> None:
        self._session.commit() if self._auto_commit else self._session.flush()


class SqlAlchemyModelEvaluationIssueRepository(ModelEvaluationIssueRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add_many(self, issues: list[ModelEvaluationIssue]) -> list[ModelEvaluationIssue]:
        models = [
            ModelEvaluationIssueModel(
                id=issue.id,
                model_evaluation_run_id=issue.model_evaluation_run_id,
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
        return [_issue_to_entity(model) for model in models]

    def list_by_model_evaluation_run_id(self, run_id: UUID) -> list[ModelEvaluationIssue]:
        statement = (
            select(ModelEvaluationIssueModel)
            .where(ModelEvaluationIssueModel.model_evaluation_run_id == run_id)
            .order_by(ModelEvaluationIssueModel.severity.asc(), ModelEvaluationIssueModel.created_at.asc())
        )
        return [_issue_to_entity(model) for model in self._session.execute(statement).scalars()]

    def _commit_or_flush(self) -> None:
        self._session.commit() if self._auto_commit else self._session.flush()


class SqlAlchemyModelPromotionGateRunRepository(ModelPromotionGateRunRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add(self, run: ModelPromotionGateRun) -> ModelPromotionGateRun:
        model = ModelPromotionGateRunModel(
            id=run.id,
            model_candidate_id=run.model_candidate_id,
            model_evaluation_run_id=run.model_evaluation_run_id,
            decision=run.decision.value,
            gate_summary=run.gate_summary,
            blocking_reasons=run.blocking_reasons,
            required_thresholds=run.required_thresholds,
            observed_metrics=run.observed_metrics,
            created_at=run.created_at,
            created_by=run.created_by,
            notes=run.notes,
        )
        self._session.add(model)
        self._commit_or_flush()
        self._session.refresh(model)
        return _gate_to_entity(model)

    def get_by_id(self, run_id: UUID) -> ModelPromotionGateRun | None:
        model = self._session.get(ModelPromotionGateRunModel, run_id)
        return _gate_to_entity(model) if model else None

    def list_by_model_candidate_id(self, candidate_id: UUID) -> list[ModelPromotionGateRun]:
        statement = (
            select(ModelPromotionGateRunModel)
            .where(ModelPromotionGateRunModel.model_candidate_id == candidate_id)
            .order_by(ModelPromotionGateRunModel.created_at.asc(), ModelPromotionGateRunModel.id.asc())
        )
        return [_gate_to_entity(model) for model in self._session.execute(statement).scalars()]

    def _commit_or_flush(self) -> None:
        self._session.commit() if self._auto_commit else self._session.flush()
