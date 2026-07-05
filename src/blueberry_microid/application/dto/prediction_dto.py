from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.prediction import Prediction
from blueberry_microid.domain.enums.predicted_label import PredictedLabel


@dataclass(frozen=True, slots=True)
class PredictionDTO:
    """Output representation of a Prediction, decoupled from the ORM model.

    There is no corresponding "CreateRequest": predictions are produced
    exclusively by an `InferenceEnginePort` implementation inside
    `ProcessAnalysisRunUseCase`, never submitted directly by a caller.
    """

    id: UUID
    analysis_run_id: UUID
    predicted_label: PredictedLabel
    confidence_score: Optional[float]
    class_probabilities: Optional[dict[str, float]]
    technical_observation: Optional[str]
    requires_human_review: bool
    created_at: datetime
    explanation: Optional[str] = None
    feature_summary: Optional[dict] = None
    quality_summary: Optional[dict] = None
    decision_trace: Optional[list] = None
    warnings: Optional[list[str]] = None

    @classmethod
    def from_entity(cls, prediction: Prediction) -> "PredictionDTO":
        return cls(
            id=prediction.id,
            analysis_run_id=prediction.analysis_run_id,
            predicted_label=prediction.predicted_label,
            confidence_score=prediction.confidence_score,
            class_probabilities=prediction.class_probabilities,
            technical_observation=prediction.technical_observation,
            requires_human_review=prediction.requires_human_review,
            created_at=prediction.created_at,
            explanation=prediction.explanation,
            feature_summary=prediction.feature_summary,
            quality_summary=prediction.quality_summary,
            decision_trace=prediction.decision_trace,
            warnings=prediction.warnings,
        )
