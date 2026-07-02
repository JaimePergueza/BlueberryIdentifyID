from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.value_objects.confidence_score import ConfidenceScore


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Prediction:
    """The preliminary, non-diagnostic result of one AnalysisRun.

    `predicted_label` is a broad visual category, never a species/genus.
    `confidence_score` is a technical score in [0, 1], not a certainty
    guarantee. An `inconclusive` label always requires human review.
    """

    analysis_run_id: UUID
    predicted_label: PredictedLabel
    id: UUID = field(default_factory=uuid4)
    confidence_score: Optional[float] = None
    class_probabilities: Optional[dict[str, float]] = None
    technical_observation: Optional[str] = None
    requires_human_review: bool = False
    created_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if self.confidence_score is not None:
            self.confidence_score = float(ConfidenceScore(self.confidence_score))
        if self.predicted_label == PredictedLabel.INCONCLUSIVE:
            self.requires_human_review = True
