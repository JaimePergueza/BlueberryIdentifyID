from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.model_promotion_decision import ModelPromotionDecision


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ModelPromotionGateRun:
    model_candidate_id: UUID
    model_evaluation_run_id: UUID
    decision: ModelPromotionDecision
    gate_summary: dict
    blocking_reasons: list[dict]
    required_thresholds: dict
    observed_metrics: dict
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_utcnow)
    created_by: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        self.decision = ModelPromotionDecision(self.decision)
