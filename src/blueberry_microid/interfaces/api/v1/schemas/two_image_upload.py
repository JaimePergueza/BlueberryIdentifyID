from uuid import UUID

from pydantic import BaseModel, Field

from blueberry_microid.domain.enums.predicted_label import PredictedLabel


class TwoImageUploadAnalysisRead(BaseModel):
    """Response for POST /api/v1/analysis/two-image-upload (Fase 40.1).

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
    confidence_score: float = Field(description="Simulated confidence in [0, 1].")
    class_probabilities: dict[str, float] = Field(
        description="Simulated probability distribution over all five preliminary classes."
    )
    requires_human_review: bool = Field(
        description="Always True for this endpoint — all preliminary uploads require expert review."
    )
    disclaimer: str = Field(
        description="Mandatory disclaimer: this result is produced by a mock engine with no diagnostic validity."
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

    model_config = {"from_attributes": True}
