from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision


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

    Formats an existing Prediction as a preliminary result.  Includes the
    current human review status (Fase 42) so callers can see whether a review
    has been submitted without fetching the full final-result endpoint.
    New review fields are optional for backward compatibility.
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
    # Human review status (Fase 42) — all optional for backward compatibility
    human_review_status: Optional[str] = Field(
        default=None,
        description=(
            "Current workflow status: pending_human_review | human_confirmed | "
            "human_corrected | inconclusive | rejected_invalid_sample."
        ),
    )
    human_review_completed: Optional[bool] = Field(
        default=None,
        description="True if any final human review has been submitted.",
    )
    latest_human_review_id: Optional[UUID] = Field(
        default=None,
        description="ID of the current final HumanReview, if one has been submitted.",
    )
    latest_human_review_decision: Optional[ReviewDecision] = Field(
        default=None,
        description="Expert decision, if a review has been submitted.",
    )
    final_label: Optional[PredictedLabel] = Field(
        default=None,
        description="Resolved final label from expert review, if available.",
    )
    reviewed_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp of the most recent final human review.",
    )

    model_config = {"from_attributes": True}
