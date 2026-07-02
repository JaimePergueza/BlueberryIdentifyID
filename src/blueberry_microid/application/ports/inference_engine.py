from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from blueberry_microid.domain.entities.analysis_run import AnalysisRun
from blueberry_microid.domain.entities.micro_image import MicroImage
from blueberry_microid.domain.entities.model_version import ModelVersion
from blueberry_microid.domain.entities.petri_image import PetriImage
from blueberry_microid.domain.enums.predicted_label import PredictedLabel


@dataclass(frozen=True, slots=True)
class InferenceOutput:
    """Result produced by an `InferenceEnginePort` implementation for one AnalysisRun.

    `predicted_label` is always one of the broad, preliminary visual
    categories in `PredictedLabel` — never a species/genus name.
    `confidence_score` is a technical score, not a certainty guarantee, and
    must never be fabricated to look more precise than the engine actually
    is (see `MockInferenceEngine` for the current, simulated implementation).
    """

    predicted_label: PredictedLabel
    confidence_score: Optional[float]
    class_probabilities: Optional[dict[str, float]]
    technical_observation: Optional[str]
    requires_human_review: bool


class InferenceEnginePort(ABC):
    """Produces an `InferenceOutput` from one AnalysisRun's multimodal inputs.

    Implementations must never import FastAPI or SQLAlchemy (this is an
    application-layer port), and must never claim real diagnostic or
    taxonomic capability unless a specific, validated implementation has
    actually earned that claim — which does not exist in this codebase yet.
    Today the only implementation is `ml.inference_engine.MockInferenceEngine`,
    a deterministic simulation used to exercise the technical pipeline.
    """

    @abstractmethod
    def process(
        self,
        *,
        analysis_run: AnalysisRun,
        petri_image: PetriImage,
        micro_image: MicroImage,
        model_version: ModelVersion,
    ) -> InferenceOutput:
        raise NotImplementedError
