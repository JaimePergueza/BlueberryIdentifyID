"""Assess whether existing Petri candidate regions support a visual count.

This is not an independently validated colony detector. Counts describe the
existing segmentation; overlapping growth and unsuitable captures abstain.
"""

from collections.abc import Mapping
import math

METHOD_VERSION = "petri-candidate-count-0.1.0"


def assess_colony_count(petri: Mapping[str, object]) -> dict:
    count = petri.get("region_count")
    sharpness = petri.get("sharpness")
    intensity = petri.get("mean_intensity")
    coverage = petri.get("colony_coverage")
    reasons: list[str] = []

    if petri.get("extraction_ok") is not True:
        reasons.append("extraction_failed")
    if petri.get("plate_detected") is not True:
        reasons.append("plate_not_detected")
    if type(count) is not int or count < 0:
        reasons.append("invalid_candidate_count")
    if not _finite(sharpness) or sharpness < 50:
        reasons.append("insufficient_focus")
    if not _finite(intensity) or not 25 <= intensity <= 230:
        reasons.append("unsuitable_exposure")
    if not _finite(coverage) or not 0 <= coverage <= 1:
        reasons.append("invalid_coverage")
    if petri.get("segmentation_conflict") is not False:
        reasons.append("segmentation_uncertain")
    if petri.get("confluent_growth_detected") is not False:
        reasons.append("connected_growth")
    if _finite(coverage) and coverage >= 0.45:
        reasons.append("high_coverage")
    if type(count) is int and count > 300:
        reasons.append("too_many_candidates")

    overlay = petri.get("visualization")
    regions = overlay.get("regions") if isinstance(overlay, Mapping) else None
    visible = len(regions) if isinstance(regions, list) else 0
    warnings = [
        "Conteo visual preliminar de regiones candidatas; requiere revisión del especialista.",
        "Una región puede corresponder a una colonia, un artefacto o varias colonias unidas.",
    ]
    if type(count) is int and visible < count:
        warnings.append("La superposición muestra solo parte de las regiones detectadas.")
    if reasons:
        warnings.append("La captura no permite un conteo automático interpretable; revise o repita la fotografía.")

    return {
        "method_version": METHOD_VERSION,
        "validation_status": "unvalidated",
        "status": "not_countable" if reasons else "preliminary",
        "estimated_count": None if reasons else count,
        "candidate_region_count": count if type(count) is int and count >= 0 else None,
        "visible_region_count": visible,
        "coverage_fraction": coverage if _finite(coverage) and 0 <= coverage <= 1 else None,
        "reason_codes": reasons,
        "warnings": warnings,
        "requires_human_review": True,
        "unit": "candidate_regions_per_plate_image",
        "cfu_per_ml": None,
    }


def _finite(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)
