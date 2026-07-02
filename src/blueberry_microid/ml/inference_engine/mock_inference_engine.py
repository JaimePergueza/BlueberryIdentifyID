import hashlib

from blueberry_microid.application.ports.inference_engine import InferenceEnginePort, InferenceOutput
from blueberry_microid.domain.entities.analysis_run import AnalysisRun
from blueberry_microid.domain.entities.micro_image import MicroImage
from blueberry_microid.domain.entities.model_version import ModelVersion
from blueberry_microid.domain.entities.petri_image import PetriImage
from blueberry_microid.domain.enums.predicted_label import PredictedLabel

# The five preliminary, non-taxonomic visual categories this system supports.
# No species/genus name is ever produced anywhere in this engine.
_LABEL_CYCLE: tuple[PredictedLabel, ...] = (
    PredictedLabel.NO_EVIDENT_GROWTH,
    PredictedLabel.SUSPICIOUS_GROWTH,
    PredictedLabel.PROBABLE_FUNGAL_GROWTH,
    PredictedLabel.PROBABLE_BACTERIAL_GROWTH,
    PredictedLabel.INCONCLUSIVE,
)

# Deliberately moderate (0.55-0.65): a simulated engine must never look more
# confident than a real, unvalidated one would be allowed to claim.
_CONFIDENCE_BY_LABEL: dict[PredictedLabel, float] = {
    PredictedLabel.NO_EVIDENT_GROWTH: 0.60,
    PredictedLabel.SUSPICIOUS_GROWTH: 0.58,
    PredictedLabel.PROBABLE_FUNGAL_GROWTH: 0.65,
    PredictedLabel.PROBABLE_BACTERIAL_GROWTH: 0.63,
    PredictedLabel.INCONCLUSIVE: 0.55,
}

_TECHNICAL_OBSERVATION = (
    "SIMULATED RESULT (mock inference engine): no real image analysis was performed "
    "on the Petri dish or microscopy image content. This output exists only to "
    "exercise the AnalysisRun -> Prediction technical pipeline end-to-end before any "
    "real or trained model exists. It carries no diagnostic or taxonomic validity and "
    "must not be treated as a real microbiological result."
)


class MockInferenceEngine(InferenceEnginePort):
    """Deterministic, non-diagnostic simulation of the multimodal inference pipeline.

    THIS IS NOT REAL IMAGE ANALYSIS. It never opens, decodes, or inspects the
    actual Petri dish or microscopy image bytes — no Pillow, no OpenCV, no
    Cellpose, no PyTorch. The predicted label is derived purely from
    `analysis_run.id` (a stable hash, not randomness), so processing the same
    AnalysisRun always yields the same result, while different runs exercise
    different branches of the pipeline for testing purposes. It exists
    exclusively to validate that AnalysisRun -> Prediction -> state
    transition works correctly before a real or trained model is ever
    introduced (see ARCHITECTURE.md for the phase this is scoped to).

    It never produces a species or genus name, and its confidence scores are
    deliberately moderate — never near-certain — to avoid any appearance of
    diagnostic reliability.
    """

    def process(
        self,
        *,
        analysis_run: AnalysisRun,
        petri_image: PetriImage,
        micro_image: MicroImage,
        model_version: ModelVersion,
    ) -> InferenceOutput:
        label = self._deterministic_label(analysis_run)
        confidence = _CONFIDENCE_BY_LABEL[label]

        return InferenceOutput(
            predicted_label=label,
            confidence_score=confidence,
            class_probabilities=self._simulated_probabilities(label),
            technical_observation=_TECHNICAL_OBSERVATION,
            requires_human_review=(label == PredictedLabel.INCONCLUSIVE),
        )

    @staticmethod
    def _deterministic_label(analysis_run: AnalysisRun) -> PredictedLabel:
        digest = hashlib.sha256(analysis_run.id.bytes).digest()
        return _LABEL_CYCLE[digest[0] % len(_LABEL_CYCLE)]

    @staticmethod
    def _simulated_probabilities(label: PredictedLabel) -> dict[str, float]:
        """A simple, deterministic (never random) distribution: the winning
        label gets its configured confidence, the remainder is split evenly
        across the other categories so the values sum to 1.0.
        """
        winning_score = _CONFIDENCE_BY_LABEL[label]
        remaining_labels = [candidate for candidate in _LABEL_CYCLE if candidate != label]
        remainder_each = round((1.0 - winning_score) / len(remaining_labels), 4)

        probabilities = {label.value: winning_score}
        probabilities.update({other.value: remainder_each for other in remaining_labels})
        return probabilities
