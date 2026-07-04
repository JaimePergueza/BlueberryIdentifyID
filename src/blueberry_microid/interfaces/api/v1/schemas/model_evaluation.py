from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CreateModelCandidateFromLocalYoloRunRequestBody(BaseModel):
    local_yolo_training_execution_run_id: UUID
    created_by: Optional[str] = None
    notes: Optional[str] = None


class RunPromotionGateRequestBody(BaseModel):
    created_by: Optional[str] = None
    notes: Optional[str] = None


class ModelCandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class ModelCandidateListResponse(BaseModel):
    model_candidates: list[ModelCandidateResponse]


class ModelEvaluationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class ModelEvaluationRunListResponse(BaseModel):
    model_evaluations: list[ModelEvaluationRunResponse]


class ModelEvaluationIssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    model_evaluation_run_id: UUID
    severity: str
    code: str
    message: str
    details: Optional[dict]
    created_at: datetime


class ModelEvaluationIssueListResponse(BaseModel):
    issues: list[ModelEvaluationIssueResponse]


class ModelPromotionGateRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class ModelPromotionGateRunListResponse(BaseModel):
    promotion_gates: list[ModelPromotionGateRunResponse]
