from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.model_evaluation_status import ModelEvaluationStatus
from blueberry_microid.domain.enums.model_promotion_decision import ModelPromotionDecision


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ModelEvaluationRun:
    model_candidate_id: UUID
    status: ModelEvaluationStatus
    decision: ModelPromotionDecision
    metrics_summary: dict
    thresholds: dict
    dataset_summary: dict
    artifact_summary: dict
    evaluation_summary: dict
    warning_count: int
    error_count: int
    info_count: int
    id: UUID = field(default_factory=uuid4)
    local_yolo_training_execution_run_id: Optional[UUID] = None
    started_at: datetime = field(default_factory=_utcnow)
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=_utcnow)
    error_message: Optional[str] = None

    def __post_init__(self) -> None:
        self.status = ModelEvaluationStatus(self.status)
        self.decision = ModelPromotionDecision(self.decision)
        if self.warning_count < 0 or self.error_count < 0 or self.info_count < 0:
            raise ValueError("issue counts cannot be negative")
