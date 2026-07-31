"""Explainable two-image morphology engine.

The engine combines classical Petri-dish and microscopy measurements. It
reports broad visual categories only, keeps confidence deliberately limited,
and records every score used by the decision. It is not a trained or
scientifically validated taxonomic classifier.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
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

_MIN_REGIONS_FOR_GROWTH = 1
_MIN_COVERAGE_FOR_GROWTH = 0.008
_MIN_EDGE_FOR_MICROSTRUCTURE = 0.03
_HIGH_EDGE_FILAMENTOUS = 0.12
_MIN_STD_CELLULAR = 20.0
_MIN_FILAMENTOUS_SCORE = 0.42
_MIN_CELLULAR_SCORE = 0.40
_MAX_CONFIDENCE = 0.65

_LABEL_CYCLE: tuple[PredictedLabel, ...] = (
    PredictedLabel.NO_EVIDENT_GROWTH,
    PredictedLabel.SUSPICIOUS_GROWTH,
    PredictedLabel.PROBABLE_FUNGAL_GROWTH,
    PredictedLabel.PROBABLE_BACTERIAL_GROWTH,
    PredictedLabel.INCONCLUSIVE,
)

PRELIMINARY_DISCLAIMER = (
    "RESULTADO MORFOLÓGICO PRELIMINAR: se analizaron píxeles reales de la caja "
    "Petri y de la microscopía mediante procesamiento clásico y reglas "
    "explicables. El motor no está validado con un conjunto etiquetado suficiente, "
    "no identifica género ni especie y no tiene alcance diagnóstico. La revisión "
    "de un especialista es obligatoria."
)


@dataclass
class PreliminaryAnalysisOutput:
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
    """Stateless, classical and explainable analysis of a paired sample."""

    def __init__(self) -> None:
        self._petri_extractor = PetriVisualSignalExtractor()
        self._micro_extractor = MicroVisualSignalExtractor()

    def analyze(
        self,
        *,
        petri_image_bytes: bytes,
        micro_image_bytes: bytes,
    ) -> PreliminaryAnalysisOutput:
        upload_id = str(uuid.uuid4())
        petri_signals = self._petri_extractor.extract(petri_image_bytes)
        micro_signals = self._micro_extractor.extract(micro_image_bytes)

        label, confidence, explanation, trace = _classify(petri_signals, micro_signals)
        warnings = list(petri_signals.warnings) + list(micro_signals.warnings)
        if not petri_signals.extraction_ok:
            warnings.insert(0, "No se pudieron extraer características de la imagen Petri.")
        if not micro_signals.extraction_ok:
            warnings.insert(0, "No se pudieron extraer características de la microscopía.")

        logger.info(
            "preliminary_morphology_analysis upload_id=%s label=%s confidence=%.3f",
            upload_id,
            label.value,
            confidence,
        )

        return PreliminaryAnalysisOutput(
            upload_id=upload_id,
            predicted_label=label,
            confidence_score=confidence,
            class_probabilities=_class_probabilities(label, confidence),
            requires_human_review=True,
            disclaimer=PRELIMINARY_DISCLAIMER,
            explanation=explanation,
            feature_summary=_build_feature_summary(petri_signals, micro_signals),
            quality_summary=_build_quality_summary(petri_signals, micro_signals),
            decision_trace=trace,
            warnings=warnings or None,
        )


def _classify(
    petri: PetriVisualSignals,
    micro: MicroVisualSignals,
) -> tuple[PredictedLabel, float, str, list[dict]]:
    trace: list[dict] = []

    if not petri.extraction_ok or not micro.extraction_ok:
        trace.append({
            "step": "quality_gate",
            "passed": False,
            "petri_extraction_ok": petri.extraction_ok,
            "micro_extraction_ok": micro.extraction_ok,
        })
        explanation = (
            "No fue posible obtener evidencia confiable de ambas imágenes. "
            "El análisis se marca como no concluyente y requiere repetir la captura."
        )
        trace.append({
            "step": "label_assigned",
            "label": PredictedLabel.INCONCLUSIVE.value,
            "confidence": 0.30,
        })
        return PredictedLabel.INCONCLUSIVE, 0.30, explanation, trace

    has_candidate_growth = (
        petri.region_count >= _MIN_REGIONS_FOR_GROWTH
        or petri.colony_coverage >= _MIN_COVERAGE_FOR_GROWTH
    )
    macro_growth_score = _clip01(
        0.52 * min(1.0, petri.colony_coverage / 0.18)
        + 0.28 * min(1.0, petri.region_count / 6.0)
        + 0.12 * min(1.0, petri.mean_texture_std / 35.0)
        + 0.08 * min(1.0, petri.edge_irregularity / 0.55)
    )
    filamentous_score = _clip01(
        0.30 * min(1.0, micro.edge_density / 0.16)
        + 0.28 * min(1.0, micro.filament_coverage / 0.12)
        + 0.22 * min(1.0, micro.branch_point_density / 0.002)
        + 0.20 * micro.elongated_component_ratio
    )
    cellular_score = _clip01(
        0.48 * min(1.0, micro.intensity_std / 45.0)
        + 0.28 * min(1.0, micro.edge_density / 0.10)
        + 0.14 * min(1.0, micro.component_count / 80.0)
        + 0.10 * min(1.0, micro.round_component_density / 0.001)
    ) * (1.0 - 0.45 * micro.elongated_component_ratio)

    trace.extend([
        {
            "step": "petri_analysis",
            "region_count": petri.region_count,
            "colony_coverage": round(petri.colony_coverage, 5),
            "mean_circularity": round(petri.mean_circularity, 4),
            "edge_irregularity": round(petri.edge_irregularity, 4),
            "mean_texture_std": round(petri.mean_texture_std, 3),
            "has_candidate_growth": has_candidate_growth,
        },
        {
            "step": "micro_analysis",
            "edge_density": round(micro.edge_density, 5),
            "filament_coverage": round(micro.filament_coverage, 5),
            "branch_point_density": round(micro.branch_point_density, 6),
            "elongated_component_ratio": round(micro.elongated_component_ratio, 4),
            "component_count": micro.component_count,
        },
        {
            "step": "evidence_fusion",
            "macro_growth_score": round(macro_growth_score, 4),
            "filamentous_score": round(filamentous_score, 4),
            "cellular_score": round(cellular_score, 4),
        },
    ])

    if not has_candidate_growth:
        confidence = _bounded_confidence(0.54 + 0.06 * (1.0 - macro_growth_score))
        explanation = (
            "No se detectaron regiones candidatas de crecimiento suficientes en la caja Petri. "
            "La conclusión se limita a ausencia de crecimiento evidente en esta captura."
        )
        return _decision(
            PredictedLabel.NO_EVIDENT_GROWTH,
            confidence,
            explanation,
            trace,
            "no_candidate_growth",
        )

    if micro.edge_density < _MIN_EDGE_FOR_MICROSTRUCTURE and micro.filament_coverage < 0.01:
        confidence = _bounded_confidence(0.43 + 0.08 * macro_growth_score)
        explanation = (
            f"La caja Petri presenta {petri.region_count} región(es) candidata(s) y una cobertura "
            f"aproximada de {petri.colony_coverage:.1%}, pero la microscopía contiene poco detalle "
            "estructural. Se reporta crecimiento sospechoso sin clasificación morfológica."
        )
        return _decision(
            PredictedLabel.SUSPICIOUS_GROWTH,
            confidence,
            explanation,
            trace,
            "growth_without_micro_support",
        )

    if micro.edge_density >= _HIGH_EDGE_FILAMENTOUS or filamentous_score >= _MIN_FILAMENTOUS_SCORE:
        confidence = _bounded_confidence(0.51 + 0.09 * filamentous_score + 0.04 * macro_growth_score)
        explanation = (
            f"Se detectaron {petri.region_count} región(es) candidatas en Petri con cobertura "
            f"{petri.colony_coverage:.1%}. En microscopía se observaron señales lineales y "
            f"ramificadas: cobertura filamentosa {micro.filament_coverage:.1%}, densidad de bordes "
            f"{micro.edge_density:.1%} y proporción de componentes alargados "
            f"{micro.elongated_component_ratio:.1%}. El patrón es compatible con crecimiento "
            "fúngico filamentoso, sin identificación taxonómica."
        )
        return _decision(
            PredictedLabel.PROBABLE_FUNGAL_GROWTH,
            confidence,
            explanation,
            trace,
            "combined_filamentous_evidence",
        )

    if micro.intensity_std >= _MIN_STD_CELLULAR and cellular_score >= _MIN_CELLULAR_SCORE:
        confidence = _bounded_confidence(0.49 + 0.09 * cellular_score + 0.03 * macro_growth_score)
        explanation = (
            f"La caja Petri presenta crecimiento candidato y la microscopía muestra una textura "
            f"celular densa (desviación de intensidad {micro.intensity_std:.1f}, densidad de bordes "
            f"{micro.edge_density:.1%}) sin predominio filamentoso. El patrón se clasifica como "
            "crecimiento bacteriano probable, sujeto a revisión experta."
        )
        return _decision(
            PredictedLabel.PROBABLE_BACTERIAL_GROWTH,
            confidence,
            explanation,
            trace,
            "combined_cellular_evidence",
        )

    explanation = (
        "La caja Petri contiene regiones candidatas de crecimiento, pero las características "
        "microscópicas no alcanzan un patrón morfológico consistente. El resultado permanece "
        "no concluyente y debe revisarse con más campos, aumento y tinción documentados."
    )
    return _decision(
        PredictedLabel.INCONCLUSIVE,
        0.40,
        explanation,
        trace,
        "ambiguous_morphology",
    )


def _decision(
    label: PredictedLabel,
    confidence: float,
    explanation: str,
    trace: list[dict],
    rule: str,
) -> tuple[PredictedLabel, float, str, list[dict]]:
    trace.append({"step": "rule_applied", "rule": rule})
    trace.append({"step": "label_assigned", "label": label.value, "confidence": confidence})
    return label, confidence, explanation, trace


def _bounded_confidence(value: float) -> float:
    return round(max(0.25, min(_MAX_CONFIDENCE, value)), 4)


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _class_probabilities(label: PredictedLabel, confidence: float) -> dict[str, float]:
    others = [candidate for candidate in _LABEL_CYCLE if candidate != label]
    remainder = max(0.0, 1.0 - confidence)
    remainder_each = remainder / float(len(others))
    probabilities = {candidate.value: remainder_each for candidate in others}
    probabilities[label.value] = confidence
    return {key: round(value, 6) for key, value in probabilities.items()}


def _build_feature_summary(petri: PetriVisualSignals, micro: MicroVisualSignals) -> dict:
    return {
        "petri": {
            "region_count": petri.region_count,
            "colony_coverage": round(petri.colony_coverage, 5),
            "mean_region_area_fraction": round(petri.mean_region_area_fraction, 5),
            "mean_circularity": round(petri.mean_circularity, 4),
            "edge_irregularity": round(petri.edge_irregularity, 4),
            "mean_texture_std": round(petri.mean_texture_std, 3),
            "mean_saturation": round(petri.mean_saturation, 4),
            "mean_hue": round(petri.mean_hue, 4),
            "mean_intensity": round(petri.mean_intensity, 2),
            "sharpness": round(petri.sharpness, 2),
            "plate_detected": petri.plate_detected,
            "plate_area_fraction": round(petri.plate_area_fraction, 4),
            "extraction_ok": petri.extraction_ok,
        },
        "micro": {
            "mean_intensity": round(micro.mean_intensity, 2),
            "intensity_std": round(micro.intensity_std, 3),
            "edge_density": round(micro.edge_density, 5),
            "filament_coverage": round(micro.filament_coverage, 5),
            "skeleton_density": round(micro.skeleton_density, 6),
            "branch_point_density": round(micro.branch_point_density, 7),
            "elongated_component_ratio": round(micro.elongated_component_ratio, 4),
            "round_component_density": round(micro.round_component_density, 7),
            "component_count": micro.component_count,
            "sharpness": round(micro.sharpness, 2),
            "field_detected": micro.field_detected,
            "field_coverage": round(micro.field_coverage, 4),
            "extraction_ok": micro.extraction_ok,
        },
    }


def _build_quality_summary(petri: PetriVisualSignals, micro: MicroVisualSignals) -> dict:
    from blueberry_microid.ml.inference_engine.micro_visual_signal_extractor import (
        _EMPTY_FIELD_EDGE_THRESHOLD,
        _EMPTY_FIELD_STD_THRESHOLD,
        _LOW_SHARPNESS_THRESHOLD as _MICRO_SHARP_THRESHOLD,
    )
    from blueberry_microid.ml.inference_engine.petri_visual_signal_extractor import (
        _LOW_SHARPNESS_THRESHOLD as _PETRI_SHARP_THRESHOLD,
        _OVEREXPOSED_MEAN,
        _UNDEREXPOSED_MEAN,
    )

    return {
        "petri_is_sharp": petri.sharpness >= _PETRI_SHARP_THRESHOLD,
        "petri_overexposed": petri.mean_intensity > _OVEREXPOSED_MEAN,
        "petri_underexposed": petri.mean_intensity < _UNDEREXPOSED_MEAN,
        "petri_plate_detected": petri.plate_detected,
        "micro_is_sharp": micro.sharpness >= _MICRO_SHARP_THRESHOLD,
        "micro_field_detected": micro.field_detected,
        "micro_appears_empty": (
            micro.intensity_std < _EMPTY_FIELD_STD_THRESHOLD
            and micro.edge_density < _EMPTY_FIELD_EDGE_THRESHOLD
        ),
        "petri_extraction_ok": petri.extraction_ok,
        "micro_extraction_ok": micro.extraction_ok,
    }
