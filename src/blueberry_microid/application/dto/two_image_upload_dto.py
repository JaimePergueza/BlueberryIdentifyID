from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.enums.predicted_label import PredictedLabel


@dataclass(frozen=True, slots=True)
class TwoImageUploadRequest:
    """Input for AnalyzeTwoUploadedImagesUseCase."""

    petri_file_name: str
    petri_mime_type: str
    petri_content: bytes
    micro_file_name: str
    micro_mime_type: str
    micro_content: bytes
    sample_code: Optional[str] = None
    notes: Optional[str] = None


@dataclass(frozen=True, slots=True)
class TwoImageUploadResult:
    """Output of AnalyzeTwoUploadedImagesUseCase.

    Contains real persisted IDs so callers can retrieve or review the
    entities later. Internal file paths are never included.
    """

    analysis_run_id: UUID
    prediction_id: UUID
    sample_id: UUID
    petri_image_id: UUID
    micro_image_id: UUID
    predicted_label: PredictedLabel
    confidence_score: float
    class_probabilities: dict[str, float]
    requires_human_review: bool
    disclaimer: str
