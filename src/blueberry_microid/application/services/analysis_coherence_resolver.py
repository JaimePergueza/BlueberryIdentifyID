"""Resolve contradictions between broad morphology classification and taxonomic differential.

The resolver operates only on automatic, non-diagnostic outputs before they are
persisted. It does not identify a microorganism. Its primary safety rule is to
abstain when a bacterial broad label conflicts with substantial filamentous
morphology.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from blueberry_microid.domain.enums.predicted_label import PredictedLabel


@dataclass(frozen=True, slots=True)
class CoherenceResolution:
    predicted_label: PredictedLabel
    confidence_score: float
    class_scores: dict[str, float]
    explanation: str | None
    warning: str | None
    assessment: dict[str, Any]


def resolve_analysis_coherence(
    *,
    predicted_label: PredictedLabel,
    confidence_score: float,
    class_scores: Mapping[str, float] | None,
    explanation: str | None,
    feature_summary: Mapping[str, Any] | None,
    quality_summary: Mapping[str, Any] | None,
    metadata: Mapping[str, Any] | None,
) -> CoherenceResolution:
    """Return a conservative automatic resolution and an explainable assessment."""

    features = _record(feature_summary)
    quality = _record(quality_summary)
    differential = _record(features.get("taxonomic_differential"))
    broad = _record(differential.get("broad_interpretation"))
    petri = _record(features.get("petri"))
    micro = _record(features.get("micro"))

    broad_filamentous = _as_float(broad.get("compatibility_index"))
    differential_available = differential.get("status") == "available"
    filament_coverage = _as_float(micro.get("filament_coverage"))
    elongated_ratio = _as_float(micro.get("elongated_component_ratio"))
    branch_density = _as_float(micro.get("branch_point_density"))
    macro_coverage = _as_float(petri.get("colony_coverage"))

    metadata_assessment = _metadata_assessment(metadata)
    quality_dimensions = _quality_dimensions(
        quality=quality,
        petri=petri,
        micro=micro,
        broad_filamentous=broad_filamentous,
        metadata_score=metadata_assessment["completeness_score"],
    )

    bacterial_vs_filamentous_conflict = (
        predicted_label == PredictedLabel.PROBABLE_BACTERIAL_GROWTH
        and differential_available
        and broad_filamentous >= 0.45
        and macro_coverage >= 0.008
        and (
            filament_coverage >= 0.04
            or elongated_ratio >= 0.08
            or branch_density > 0
        )
    )

    scores = _normalise_scores(class_scores)
    assessment: dict[str, Any] = {
        "engine": {"name": "AnalysisCoherenceResolver", "version": "0.1.0"},
        "status": "conflict" if bacterial_vs_filamentous_conflict else "coherent",
        "score_semantics": (
            "Las cifras son puntuaciones heurísticas no calibradas; no son probabilidades científicas."
        ),
        "automatic_label_before_resolution": predicted_label.value,
        "broad_filamentous_compatibility": round(broad_filamentous, 4),
        "conflicts": [],
        "quality_dimensions": quality_dimensions,
        "metadata": metadata_assessment,
    }

    if bacterial_vs_filamentous_conflict:
        conflict_message = (
            "La clasificación general favoreció un patrón celular/bacteriano, pero la "
            "macroscopía y el diferencial muestran evidencia filamentosa sustancial. "
            "Las señales son contradictorias o podrían corresponder a una muestra mixta."
        )
        assessment["conflicts"].append(
            {
                "type": "bacterial_vs_filamentous",
                "message": conflict_message,
                "automatic_action": "abstain_as_inconclusive",
            }
        )
        assessment["resolved_label"] = PredictedLabel.INCONCLUSIVE.value
        resolved_scores = _scores_with_inconclusive_priority(scores, target=0.42)
        resolved_explanation = (
            f"{conflict_message} El resultado automático se marca como no concluyente y "
            "requiere revisión de varios campos microscópicos, tinción documentada y, "
            "cuando proceda, aislamiento o confirmación molecular."
        )
        return CoherenceResolution(
            predicted_label=PredictedLabel.INCONCLUSIVE,
            confidence_score=0.40,
            class_scores=resolved_scores,
            explanation=resolved_explanation,
            warning=(
                "Se detectó conflicto entre evidencia celular y filamentosa; no se emite "
                "una categoría bacteriana o fúngica automática."
            ),
            assessment=assessment,
        )

    assessment["resolved_label"] = predicted_label.value
    warning = None
    if metadata_assessment["status"] == "insufficient":
        warning = (
            "Faltan metadatos experimentales importantes; la interpretación taxonómica "
            "debe considerarse de baja suficiencia aunque las imágenes sean técnicamente válidas."
        )
    return CoherenceResolution(
        predicted_label=predicted_label,
        confidence_score=confidence_score,
        class_scores=scores,
        explanation=explanation,
        warning=warning,
        assessment=assessment,
    )


def _metadata_assessment(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    values = _record(metadata)
    required = {
        "lot_code": "Lote",
        "origin": "Origen",
        "collection_date": "Fecha de recolección",
        "culture_medium": "Medio de cultivo",
        "incubation_temperature_c": "Temperatura de incubación",
        "incubation_time_hours": "Tiempo de incubación",
        "magnification": "Aumento microscópico",
        "microscope_type": "Tipo de microscopio",
        "staining_method": "Tinción o medio de montaje",
    }
    missing = [label for key, label in required.items() if _missing(values.get(key))]
    completeness = (len(required) - len(missing)) / len(required)
    if completeness >= 0.78:
        status = "sufficient"
    elif completeness >= 0.45:
        status = "partial"
    else:
        status = "insufficient"
    return {
        "status": status,
        "completeness_score": round(completeness, 4),
        "present_count": len(required) - len(missing),
        "required_count": len(required),
        "missing_fields": missing,
    }


def _quality_dimensions(
    *,
    quality: Mapping[str, Any],
    petri: Mapping[str, Any],
    micro: Mapping[str, Any],
    broad_filamentous: float,
    metadata_score: float,
) -> dict[str, Any]:
    technical_score = _as_float(quality.get("quality_score"))
    segmentation_ok = bool(petri.get("plate_detected")) and bool(micro.get("field_detected"))
    if bool(petri.get("segmentation_conflict")):
        segmentation_ok = False
    morphology_score = max(
        broad_filamentous,
        min(1.0, _as_float(petri.get("colony_coverage")) / 0.18),
    )
    return {
        "technical_capture": {
            "score": round(technical_score, 4),
            "status": _dimension_status(technical_score),
        },
        "segmentation": {
            "score": 1.0 if segmentation_ok else 0.35,
            "status": "sufficient" if segmentation_ok else "insufficient",
        },
        "morphological_sufficiency": {
            "score": round(morphology_score, 4),
            "status": _dimension_status(morphology_score),
        },
        "metadata_sufficiency": {
            "score": round(metadata_score, 4),
            "status": _dimension_status(metadata_score),
        },
    }


def _scores_with_inconclusive_priority(
    scores: Mapping[str, float],
    *,
    target: float,
) -> dict[str, float]:
    keys = [label.value for label in PredictedLabel]
    remaining_keys = [key for key in keys if key != PredictedLabel.INCONCLUSIVE.value]
    current_remaining = sum(max(0.0, float(scores.get(key, 0.0))) for key in remaining_keys)
    remainder = 1.0 - target
    if current_remaining <= 0:
        each = remainder / len(remaining_keys)
        resolved = {key: each for key in remaining_keys}
    else:
        resolved = {
            key: remainder * max(0.0, float(scores.get(key, 0.0))) / current_remaining
            for key in remaining_keys
        }
    resolved[PredictedLabel.INCONCLUSIVE.value] = target
    return {key: round(value, 6) for key, value in resolved.items()}


def _normalise_scores(scores: Mapping[str, float] | None) -> dict[str, float]:
    values = {
        label.value: max(0.0, float((scores or {}).get(label.value, 0.0)))
        for label in PredictedLabel
    }
    total = sum(values.values())
    if total <= 0:
        each = 1.0 / len(values)
        return {key: round(each, 6) for key in values}
    return {key: round(value / total, 6) for key, value in values.items()}


def _dimension_status(score: float) -> str:
    if score >= 0.75:
        return "sufficient"
    if score >= 0.45:
        return "partial"
    return "insufficient"


def _missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _record(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_float(value: Any) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0
