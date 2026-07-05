from dataclasses import dataclass

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


@dataclass(frozen=True, slots=True)
class TwoImageUploadResult:
    """Output of AnalyzeTwoUploadedImagesUseCase.

    Paths to stored images are deliberately excluded — they must never be
    surfaced to API callers (see CLAUDE.md).
    """

    upload_id: str
    predicted_label: PredictedLabel
    confidence_score: float
    class_probabilities: dict[str, float]
    requires_human_review: bool
    disclaimer: str
