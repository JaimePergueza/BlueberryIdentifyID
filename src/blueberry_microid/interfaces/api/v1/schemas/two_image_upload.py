from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from blueberry_microid.domain.enums.predicted_label import PredictedLabel


class TwoImageUploadAnalysisRead(BaseModel):
    """Response for POST /api/v1/analysis/two-image-upload (Fase 40.1 / 41).

    All entities are persisted; the response includes real DB identifiers so
    the caller can retrieve or review the AnalysisRun later.
    Internal file paths are never included.
    """

    analysis_run_id: UUID = Field(description="Persisted AnalysisRun identifier.")
    prediction_id: UUID = Field(description="Persisted Prediction identifier.")
    sample_id: UUID = Field(description="Persisted Sample identifier.")
    petri_image_id: UUID = Field(description="Persisted PetriImage identifier.")
    micro_image_id: UUID = Field(description="Persisted MicroImage identifier.")
    predicted_label: PredictedLabel = Field(
        description="Preliminary visual category (non-diagnostic, non-taxonomic)."
    )
    confidence_score: float = Field(description="Heuristic confidence score in [0, 1].")
    class_probabilities: dict[str, float] = Field(
        description="Probability distribution over all five preliminary classes."
    )
    requires_human_review: bool = Field(
        description="Always True for this endpoint — all preliminary uploads require expert review."
    )
    disclaimer: str = Field(
        description="Mandatory disclaimer: results carry no diagnostic or taxonomic validity."
    )
    explanation: Optional[str] = Field(
        default=None,
        description="Human-readable description of the heuristic signals that led to this label.",
    )
    feature_summary: Optional[dict[str, Any]] = Field(
        default=None,
        description="Extracted visual feature values from both images (Petri and microscopy).",
    )
    quality_summary: Optional[dict[str, Any]] = Field(
        default=None,
        description="Image quality flags (sharpness, exposure, empty field detection).",
    )
    decision_trace: Optional[list[Any]] = Field(
        default=None,
        description="Step-by-step trace of the heuristic rules evaluated.",
    )
    warnings: Optional[list[str]] = Field(
        default=None,
        description="Non-blocking image quality or extraction warnings.",
    )

    model_config = {"from_attributes": True}


class PreliminaryResultRead(BaseModel):
    """Response for GET /api/v1/analysis-runs/{id}/preliminary-result.

    Formats an existing Prediction as a preliminary result, with the same
    disclaimer and label structure as TwoImageUploadAnalysisRead.
    """

    analysis_run_id: str
    predicted_label: PredictedLabel
    confidence_score: float | None
    class_probabilities: dict[str, float] | None
    requires_human_review: bool
    technical_observation: str | None
    disclaimer: str
    explanation: Optional[str] = None
    feature_summary: Optional[dict[str, Any]] = None
    quality_summary: Optional[dict[str, Any]] = None
    decision_trace: Optional[list[Any]] = None
    warnings: Optional[list[str]] = None

    model_config = {"from_attributes": True}
