from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.model_candidate import ModelCandidate
from blueberry_microid.domain.entities.model_evaluation_issue import ModelEvaluationIssue
from blueberry_microid.domain.entities.model_evaluation_run import ModelEvaluationRun
from blueberry_microid.domain.entities.model_promotion_gate_run import ModelPromotionGateRun


@dataclass(frozen=True)
class CreateModelCandidateFromLocalTrainingRunRequest:
    local_yolo_training_execution_run_id: UUID
    created_by: Optional[str] = None
    notes: Optional[str] = None


@dataclass(frozen=True)
class ModelCandidateDTO:
    id: UUID
    local_yolo_training_execution_run_id: Optional[UUID]
    detection_training_run_id: Optional[UUID]
    model_version_id: Optional[UUID]
    candidate_kind: str
    status: str
    model_artifact_path: str
    model_artifact_checksum_sha256: str
    model_artifact_size_bytes: int
    metrics_artifact_path: Optional[str]
    config_artifact_path: Optional[str]
    source_summary: dict
    created_at: datetime
    created_by: Optional[str]
    notes: Optional[str]

    @classmethod
    def from_entity(cls, entity: ModelCandidate) -> "ModelCandidateDTO":
        return cls(
            id=entity.id,
            local_yolo_training_execution_run_id=entity.local_yolo_training_execution_run_id,
            detection_training_run_id=entity.detection_training_run_id,
            model_version_id=entity.model_version_id,
            candidate_kind=entity.candidate_kind.value,
            status=entity.status.value,
            model_artifact_path=entity.model_artifact_path,
            model_artifact_checksum_sha256=entity.model_artifact_checksum_sha256,
            model_artifact_size_bytes=entity.model_artifact_size_bytes,
            metrics_artifact_path=entity.metrics_artifact_path,
            config_artifact_path=entity.config_artifact_path,
            source_summary=entity.source_summary,
            created_at=entity.created_at,
            created_by=entity.created_by,
            notes=entity.notes,
        )


@dataclass(frozen=True)
class ModelEvaluationRunDTO:
    id: UUID
    model_candidate_id: UUID
    local_yolo_training_execution_run_id: Optional[UUID]
    status: str
    decision: str
    metrics_summary: dict
    thresholds: dict
    dataset_summary: dict
    artifact_summary: dict
    evaluation_summary: dict
    started_at: datetime
    completed_at: Optional[datetime]
    created_at: datetime
    error_message: Optional[str]
    warning_count: int
    error_count: int
    info_count: int

    @classmethod
    def from_entity(cls, entity: ModelEvaluationRun) -> "ModelEvaluationRunDTO":
        return cls(
            id=entity.id,
            model_candidate_id=entity.model_candidate_id,
            local_yolo_training_execution_run_id=entity.local_yolo_training_execution_run_id,
            status=entity.status.value,
            decision=entity.decision.value,
            metrics_summary=entity.metrics_summary,
            thresholds=entity.thresholds,
            dataset_summary=entity.dataset_summary,
            artifact_summary=entity.artifact_summary,
            evaluation_summary=entity.evaluation_summary,
            started_at=entity.started_at,
            completed_at=entity.completed_at,
            created_at=entity.created_at,
            error_message=entity.error_message,
            warning_count=entity.warning_count,
            error_count=entity.error_count,
            info_count=entity.info_count,
        )


@dataclass(frozen=True)
class ModelEvaluationIssueDTO:
    id: UUID
    model_evaluation_run_id: UUID
    severity: str
    code: str
    message: str
    details: Optional[dict]
    created_at: datetime

    @classmethod
    def from_entity(cls, entity: ModelEvaluationIssue) -> "ModelEvaluationIssueDTO":
        return cls(
            id=entity.id,
            model_evaluation_run_id=entity.model_evaluation_run_id,
            severity=entity.severity.value,
            code=entity.code,
            message=entity.message,
            details=entity.details,
            created_at=entity.created_at,
        )


@dataclass(frozen=True)
class ModelPromotionGateRunDTO:
    id: UUID
    model_candidate_id: UUID
    model_evaluation_run_id: UUID
    decision: str
    gate_summary: dict
    blocking_reasons: list[dict]
    required_thresholds: dict
    observed_metrics: dict
    created_at: datetime
    created_by: Optional[str]
    notes: Optional[str]

    @classmethod
    def from_entity(cls, entity: ModelPromotionGateRun) -> "ModelPromotionGateRunDTO":
        return cls(
            id=entity.id,
            model_candidate_id=entity.model_candidate_id,
            model_evaluation_run_id=entity.model_evaluation_run_id,
            decision=entity.decision.value,
            gate_summary=entity.gate_summary,
            blocking_reasons=entity.blocking_reasons,
            required_thresholds=entity.required_thresholds,
            observed_metrics=entity.observed_metrics,
            created_at=entity.created_at,
            created_by=entity.created_by,
            notes=entity.notes,
        )
