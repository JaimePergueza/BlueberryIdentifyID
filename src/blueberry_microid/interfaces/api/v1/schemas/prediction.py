from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from blueberry_microid.domain.enums.predicted_label import PredictedLabel


class PredictionRead(BaseModel):
    """Representation of a Prediction returned by the API.

    System-generated only — there is no PredictionCreate schema, since
    predictions come from the inference engine, never directly from a client.
    `predicted_label` is a broad visual category, never a species/genus.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    analysis_run_id: UUID
    predicted_label: PredictedLabel
    confidence_score: Optional[float]
    class_probabilities: Optional[dict[str, float]]
    technical_observation: Optional[str]
    requires_human_review: bool
    created_at: datetime

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence_score(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and not (0.0 <= value <= 1.0):
            raise ValueError(f"confidence_score must be between 0 and 1, got {value}")
        return value
