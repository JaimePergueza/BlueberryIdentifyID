"""Preliminary two-image analysis engine (stateless, non-diagnostic).

This engine applies the same deterministic label logic as MockInferenceEngine
but operates on raw bytes (no domain entities, no DB lookups) so it can be
used by the stateless two-image upload endpoint.

THIS IS NOT REAL IMAGE ANALYSIS.  No pixels are inspected — the label is
derived from a UUID generated for each upload call.  Results carry no
diagnostic or taxonomic validity and must not be used as a substitute for
expert microbiological assessment.
"""

import hashlib
import uuid
from dataclasses import dataclass

from blueberry_microid.domain.enums.predicted_label import PredictedLabel

_LABEL_CYCLE: tuple[PredictedLabel, ...] = (
    PredictedLabel.NO_EVIDENT_GROWTH,
    PredictedLabel.SUSPICIOUS_GROWTH,
    PredictedLabel.PROBABLE_FUNGAL_GROWTH,
    PredictedLabel.PROBABLE_BACTERIAL_GROWTH,
    PredictedLabel.INCONCLUSIVE,
)

_CONFIDENCE_BY_LABEL: dict[PredictedLabel, float] = {
    PredictedLabel.NO_EVIDENT_GROWTH: 0.60,
    PredictedLabel.SUSPICIOUS_GROWTH: 0.58,
    PredictedLabel.PROBABLE_FUNGAL_GROWTH: 0.65,
    PredictedLabel.PROBABLE_BACTERIAL_GROWTH: 0.63,
    PredictedLabel.INCONCLUSIVE: 0.55,
}

PRELIMINARY_DISCLAIMER = (
    "SIMULATED RESULT (mock inference engine — Fase 40 preliminary endpoint): "
    "no real image analysis was performed on the uploaded Petri dish or "
    "microscopy image content.  This preliminary result exists only to exercise "
    "the two-image upload pipeline before any real or trained model is available. "
    "It carries no diagnostic or taxonomic validity and must not be treated as a "
    "real microbiological result or a substitute for expert assessment."
)


@dataclass(frozen=True, slots=True)
class PreliminaryAnalysisOutput:
    """Result of a single preliminary two-image upload call."""

    upload_id: str
    predicted_label: PredictedLabel
    confidence_score: float
    class_probabilities: dict[str, float]
    requires_human_review: bool
    disclaimer: str


class PreliminaryTwoImageAnalysisEngine:
    """Stateless, non-diagnostic preliminary analysis over two uploaded images.

    Accepts raw bytes for the Petri dish image and the microscopy image.
    Does NOT open, decode, or inspect their pixel content — the label is
    derived from a fresh UUID generated per call, exactly mirroring the
    MockInferenceEngine strategy but without requiring domain entities or a DB.

    Lives in ``ml/`` because it is an inference-layer component (same
    classification as MockInferenceEngine), but it is intentionally decoupled
    from the AnalysisRun/Prediction persistence pipeline used by the main
    workflow.  It must not be used for production inference.
    """

    def analyze(
        self,
        *,
        petri_image_bytes: bytes,
        micro_image_bytes: bytes,
    ) -> PreliminaryAnalysisOutput:
        upload_id = str(uuid.uuid4())
        label = self._deterministic_label(upload_id)
        confidence = _CONFIDENCE_BY_LABEL[label]

        return PreliminaryAnalysisOutput(
            upload_id=upload_id,
            predicted_label=label,
            confidence_score=confidence,
            class_probabilities=self._simulated_probabilities(label),
            requires_human_review=(label == PredictedLabel.INCONCLUSIVE),
            disclaimer=PRELIMINARY_DISCLAIMER,
        )

    @staticmethod
    def _deterministic_label(upload_id: str) -> PredictedLabel:
        digest = hashlib.sha256(upload_id.encode()).digest()
        return _LABEL_CYCLE[digest[0] % len(_LABEL_CYCLE)]

    @staticmethod
    def _simulated_probabilities(label: PredictedLabel) -> dict[str, float]:
        winning_score = _CONFIDENCE_BY_LABEL[label]
        remaining = [c for c in _LABEL_CYCLE if c != label]
        remainder_each = round((1.0 - winning_score) / len(remaining), 4)
        probs = {label.value: winning_score}
        probs.update({other.value: remainder_each for other in remaining})
        return probs
