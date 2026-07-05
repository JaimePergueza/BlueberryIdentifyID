from pydantic import BaseModel, Field

from blueberry_microid.domain.enums.predicted_label import PredictedLabel


class TwoImageUploadAnalysisRead(BaseModel):
    """Response for POST /api/v1/analysis/two-image-upload.

    Internal file paths are never included — only the upload_id, the
    preliminary visual label and supporting metadata, and a mandatory
    disclaimer that this is a non-diagnostic simulated result.
    """

    upload_id: str = Field(description="Unique identifier for this upload call.")
    predicted_label: PredictedLabel = Field(
        description="Preliminary visual category (non-diagnostic, non-taxonomic)."
    )
    confidence_score: float = Field(description="Simulated confidence in [0, 1].")
    class_probabilities: dict[str, float] = Field(
        description="Simulated probability distribution over all five preliminary classes."
    )
    requires_human_review: bool = Field(
        description="True when the label is 'inconclusive' and human verification is recommended."
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
