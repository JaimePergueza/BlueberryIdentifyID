"""Preliminary two-image analysis engine using real image features (Fase 41).

Reads actual pixel content from both uploaded images via classical (non-deep-
learning) feature extraction and applies transparent heuristic rules to assign
a preliminary visual label.

This engine is NOT a validated classifier.  It produces preliminary visual
categories with low confidence scores to reflect the absence of scientific
validation.  Results require human expert review.  No species, genus, or
diagnostic conclusion is ever asserted.

Allowed libraries: Pillow, numpy, OpenCV (opencv-python-headless).
Forbidden: YOLO, torch, ultralytics, TensorFlow, any deep learning.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.ml.inference_engine.micro_visual_signal_extractor import (
    MicroVisualSignalExtractor,
    MicroVisualSignals,
)
from blueberry_microid.ml.inference_engine.petri_visual_signal_extractor import (
    PetriVisualSignalExtractor,
    PetriVisualSignals,
)

logger = logging.getLogger("blueberry_microid.ml.preliminary_two_image_analysis_engine")

# ──────────────────────────────────────────────────────────────────────────────
# Heuristic thresholds
# All values are intentionally conservative.  They are tunable by domain
# experts without touching classification logic.
# ──────────────────────────────────────────────────────────────────────────────
_MIN_REGIONS_FOR_GROWTH = 1
_MIN_COVERAGE_FOR_GROWTH = 0.01   # 1 % of Petri plate area
_MIN_EDGE_FOR_MICROSTRUCTURE = 0.05   # 5 % edge pixels = some structure present
_HIGH_EDGE_FILAMENTOUS = 0.12         # 12 % edge pixels → possible filamentous morphology
_MIN_STD_CELLULAR = 20.0              # grayscale std threshold for cellular density

# Confidence capped well below mock engine's upper bound (~0.75) to reflect
# that heuristic signals are unvalidated.
_CONF_NO_GROWTH = 0.55
_CONF_SUSPICIOUS = 0.48
_CONF_FUNGAL = 0.55
_CONF_BACTERIAL = 0.52
_CONF_INCONCLUSIVE = 0.40

_LABEL_CYCLE: tuple[PredictedLabel, ...] = (
    PredictedLabel.NO_EVIDENT_GROWTH,
    PredictedLabel.SUSPICIOUS_GROWTH,
    PredictedLabel.PROBABLE_FUNGAL_GROWTH,
    PredictedLabel.PROBABLE_BACTERIAL_GROWTH,
    PredictedLabel.INCONCLUSIVE,
)

PRELIMINARY_DISCLAIMER = (
    "PRELIMINARY RESULT (classical heuristic engine — Fase 41): pixel signals "
    "from the uploaded Petri dish and microscopy images were analysed using "
    "classical, non-trained image processing rules.  This result has not been "
    "validated against a labelled dataset and carries no diagnostic or taxonomic "
    "validity.  It must not be treated as a real microbiological finding or a "
    "substitute for expert assessment.  Human expert review is mandatory."
)


@dataclass
class PreliminaryAnalysisOutput:
    """Result of a single preliminary two-image upload call (Fase 41)."""

    upload_id: str
    predicted_label: PredictedLabel
    confidence_score: float
    class_probabilities: dict[str, float]
    requires_human_review: bool
    disclaimer: str
    explanation: Optional[str] = None
    feature_summary: Optional[dict] = None
    quality_summary: Optional[dict] = None
    decision_trace: Optional[list] = None
    warnings: Optional[list[str]] = None


class PreliminaryTwoImageAnalysisEngine:
    """Stateless preliminary analysis over two uploaded images using real features.

    Accepts raw bytes for the Petri dish image and the microscopy image,
    extracts classical visual signals from each, and applies transparent
    heuristic rules to produce a preliminary visual label.

    Lives in ``ml/`` as an inference-layer component.  It must not be used
    for production inference and does not replace ``MockInferenceEngine``.
    """

    def __init__(self) -> None:
        self._petri_extractor = PetriVisualSignalExtractor()
        self._micro_extractor = MicroVisualSignalExtractor()

    def analyze(
        self,
        *,
        petri_image_bytes: bytes,
        micro_image_bytes: bytes,
    ) -> PreliminaryAnalysisOutput:
        import uuid
        upload_id = str(uuid.uuid4())

        petri_signals = self._petri_extractor.extract(petri_image_bytes)
        micro_signals = self._micro_extractor.extract(micro_image_bytes)

        label, confidence, explanation, trace = _classify(petri_signals, micro_signals)
        warnings = list(petri_signals.warnings) + list(micro_signals.warnings)

        feature_summary = _build_feature_summary(petri_signals, micro_signals)
        quality_summary = _build_quality_summary(petri_signals, micro_signals)

        if not petri_signals.extraction_ok:
            warnings.insert(0, "Petri image features could not be extracted; label is based only on micro signals.")
        if not micro_signals.extraction_ok:
            warnings.insert(0, "Micro image features could not be extracted; label is based only on Petri signals.")

        logger.info(
            "preliminary_analysis upload_id=%s label=%s confidence=%.3f",
            upload_id, label.value, confidence,
        )

        return PreliminaryAnalysisOutput(
            upload_id=upload_id,
            predicted_label=label,
            confidence_score=confidence,
            class_probabilities=_class_probabilities(label, confidence),
            requires_human_review=True,
            disclaimer=PRELIMINARY_DISCLAIMER,
            explanation=explanation,
            feature_summary=feature_summary,
            quality_summary=quality_summary,
            decision_trace=trace,
            warnings=warnings or None,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Internal helpers — delegate to module-level functions for testability
    # ──────────────────────────────────────────────────────────────────────────


def _classify(
    petri: PetriVisualSignals,
    micro: MicroVisualSignals,
) -> tuple[PredictedLabel, float, str, list[dict]]:
        """Apply ordered heuristic rules; return (label, confidence, explanation, trace)."""
        trace: list[dict] = []

        has_candidate_growth = (
            petri.region_count >= _MIN_REGIONS_FOR_GROWTH
            or petri.colony_coverage >= _MIN_COVERAGE_FOR_GROWTH
        )
        trace.append({
            "step": "petri_analysis",
            "region_count": petri.region_count,
            "colony_coverage": round(petri.colony_coverage, 5),
            "mean_saturation": round(petri.mean_saturation, 4),
            "sharpness": round(petri.sharpness, 2),
            "has_candidate_growth": has_candidate_growth,
        })
        trace.append({
            "step": "micro_analysis",
            "edge_density": round(micro.edge_density, 5),
            "intensity_std": round(micro.intensity_std, 3),
            "sharpness": round(micro.sharpness, 2),
        })

        # Rule 1: no Petri evidence
        if not has_candidate_growth:
            explanation = (
                "No candidate growth regions were detected in the Petri dish image. "
                "The visible area appears consistent with an uninoculated or clear plate."
            )
            trace.append({"step": "rule_applied", "rule": "no_candidate_growth",
                          "reason": "region_count=0 and coverage below threshold"})
            trace.append({"step": "label_assigned", "label": PredictedLabel.NO_EVIDENT_GROWTH.value,
                          "confidence": _CONF_NO_GROWTH})
            return PredictedLabel.NO_EVIDENT_GROWTH, _CONF_NO_GROWTH, explanation, trace

        # Rule 2: Petri shows growth but microscopy shows little structure
        if micro.edge_density < _MIN_EDGE_FOR_MICROSTRUCTURE:
            explanation = (
                f"Candidate growth regions detected in the Petri dish image "
                f"({petri.region_count} region(s), coverage {petri.colony_coverage:.1%}), "
                f"but the microscopy image shows low structural detail "
                f"(edge density {micro.edge_density:.1%}). "
                "Growth signal is ambiguous; suspicious pattern cannot be confirmed."
            )
            trace.append({"step": "rule_applied", "rule": "low_micro_structure",
                          "reason": f"edge_density {micro.edge_density:.4f} < threshold {_MIN_EDGE_FOR_MICROSTRUCTURE}"})
            trace.append({"step": "label_assigned", "label": PredictedLabel.SUSPICIOUS_GROWTH.value,
                          "confidence": _CONF_SUSPICIOUS})
            return PredictedLabel.SUSPICIOUS_GROWTH, _CONF_SUSPICIOUS, explanation, trace

        # Rule 3: high edge density — possibly filamentous morphology
        if micro.edge_density >= _HIGH_EDGE_FILAMENTOUS:
            explanation = (
                f"Candidate growth regions detected in the Petri dish image "
                f"({petri.region_count} region(s), coverage {petri.colony_coverage:.1%}). "
                f"The microscopy image shows high structural complexity "
                f"(edge density {micro.edge_density:.1%}), which may be consistent "
                "with a branching or filamentous morphology. "
                "No taxonomic identification is made."
            )
            trace.append({"step": "rule_applied", "rule": "high_edge_filamentous",
                          "reason": f"edge_density {micro.edge_density:.4f} >= threshold {_HIGH_EDGE_FILAMENTOUS}"})
            trace.append({"step": "label_assigned", "label": PredictedLabel.PROBABLE_FUNGAL_GROWTH.value,
                          "confidence": _CONF_FUNGAL})
            return PredictedLabel.PROBABLE_FUNGAL_GROWTH, _CONF_FUNGAL, explanation, trace

        # Rule 4: moderate edge density with cellular variance — possibly cellular morphology
        if micro.intensity_std >= _MIN_STD_CELLULAR:
            explanation = (
                f"Candidate growth regions detected in the Petri dish image "
                f"({petri.region_count} region(s), coverage {petri.colony_coverage:.1%}). "
                f"The microscopy image shows moderate structural density "
                f"(edge density {micro.edge_density:.1%}, intensity std {micro.intensity_std:.1f}), "
                "which may be consistent with a dense cellular morphology. "
                "No taxonomic identification is made."
            )
            trace.append({"step": "rule_applied", "rule": "moderate_cellular_density",
                          "reason": (f"edge_density {micro.edge_density:.4f} in range and "
                                     f"intensity_std {micro.intensity_std:.2f} >= {_MIN_STD_CELLULAR}")})
            trace.append({"step": "label_assigned", "label": PredictedLabel.PROBABLE_BACTERIAL_GROWTH.value,
                          "confidence": _CONF_BACTERIAL})
            return PredictedLabel.PROBABLE_BACTERIAL_GROWTH, _CONF_BACTERIAL, explanation, trace

        # Rule 5: signals present but ambiguous
        explanation = (
            "Candidate growth regions were detected in the Petri dish image, "
            "but the visual signals from the microscopy image do not match any "
            "heuristic pattern unambiguously. Expert review is required."
        )
        trace.append({"step": "rule_applied", "rule": "ambiguous_signals",
                      "reason": "no rule produced a definitive match"})
        trace.append({"step": "label_assigned", "label": PredictedLabel.INCONCLUSIVE.value,
                      "confidence": _CONF_INCONCLUSIVE})
        return PredictedLabel.INCONCLUSIVE, _CONF_INCONCLUSIVE, explanation, trace

def _class_probabilities(label: PredictedLabel, confidence: float) -> dict[str, float]:
        others = [c for c in _LABEL_CYCLE if c != label]
        remainder_each = round((1.0 - confidence) / len(others), 4)
        probs = {label.value: confidence}
        probs.update({other.value: remainder_each for other in others})
        return probs

def _build_feature_summary(petri: PetriVisualSignals, micro: MicroVisualSignals) -> dict:
        return {
            "petri": {
                "region_count": petri.region_count,
                "colony_coverage": round(petri.colony_coverage, 5),
                "mean_saturation": round(petri.mean_saturation, 4),
                "mean_intensity": round(petri.mean_intensity, 2),
                "sharpness": round(petri.sharpness, 2),
                "extraction_ok": petri.extraction_ok,
            },
            "micro": {
                "mean_intensity": round(micro.mean_intensity, 2),
                "intensity_std": round(micro.intensity_std, 3),
                "edge_density": round(micro.edge_density, 5),
                "sharpness": round(micro.sharpness, 2),
                "extraction_ok": micro.extraction_ok,
            },
        }

def _build_quality_summary(petri: PetriVisualSignals, micro: MicroVisualSignals) -> dict:
        from blueberry_microid.ml.inference_engine.petri_visual_signal_extractor import (
            _LOW_SHARPNESS_THRESHOLD as _PETRI_SHARP_THRESHOLD,
            _OVEREXPOSED_MEAN,
            _UNDEREXPOSED_MEAN,
        )
        from blueberry_microid.ml.inference_engine.micro_visual_signal_extractor import (
            _LOW_SHARPNESS_THRESHOLD as _MICRO_SHARP_THRESHOLD,
            _EMPTY_FIELD_STD_THRESHOLD,
            _EMPTY_FIELD_EDGE_THRESHOLD,
        )
        return {
            "petri_is_sharp": petri.sharpness >= _PETRI_SHARP_THRESHOLD,
            "petri_overexposed": petri.mean_intensity > _OVEREXPOSED_MEAN,
            "petri_underexposed": petri.mean_intensity < _UNDEREXPOSED_MEAN,
            "micro_is_sharp": micro.sharpness >= _MICRO_SHARP_THRESHOLD,
            "micro_appears_empty": (
                micro.intensity_std < _EMPTY_FIELD_STD_THRESHOLD
                and micro.edge_density < _EMPTY_FIELD_EDGE_THRESHOLD
            ),
            "petri_extraction_ok": petri.extraction_ok,
            "micro_extraction_ok": micro.extraction_ok,
        }
