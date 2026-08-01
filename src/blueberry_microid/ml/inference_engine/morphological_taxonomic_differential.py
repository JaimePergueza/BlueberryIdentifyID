"""Conservative, explainable morphology-based taxonomic differential.

This module does not identify a genus or species. It translates the classical
Petri and microscopy measurements into a limited differential of visual
compatibility hypotheses. Genus-like scores are deliberately capped below
50 %, are not calibrated probabilities, and always require expert and
molecular confirmation.
"""

from __future__ import annotations

from typing import Any

from blueberry_microid.domain.enums.predicted_label import PredictedLabel

DIFFERENTIAL_ENGINE_NAME = "MorphologicalDifferentialEngine"
DIFFERENTIAL_ENGINE_VERSION = "0.1.0"
_MAX_GENUS_COMPATIBILITY = 0.49


def build_taxonomic_differential(
    *,
    predicted_label: PredictedLabel,
    feature_summary: dict | None,
    quality_summary: dict | None,
) -> dict:
    """Build a non-diagnostic differential from already extracted signals."""

    features = _record(feature_summary)
    quality = _record(quality_summary)
    petri = _record(features.get("petri"))
    micro = _record(features.get("micro"))
    quality_status = str(quality.get("overall_status") or "unknown")

    base = {
        "engine": {
            "name": DIFFERENTIAL_ENGINE_NAME,
            "version": DIFFERENTIAL_ENGINE_VERSION,
        },
        "scope": "diferencial morfológico visual no diagnóstico",
        "score_semantics": (
            "Los índices expresan compatibilidad heurística con rasgos visibles; "
            "no son probabilidades científicas ni identificaciones taxonómicas."
        ),
        "primary_hypothesis": None,
        "candidates": [],
        "confirmation_required": [
            "Revisión de varios campos microscópicos maduros por un especialista.",
            "Registrar aumento, tinción o medio de montaje, medio de cultivo, temperatura y tiempo de incubación.",
            "Confirmación molecular mediante ITS y, cuando corresponda, un marcador secundario como BenA o CaM.",
        ],
        "limitations": [
            "El motor todavía no reconoce semánticamente conidióforos, vesículas, métulas, fiálides ni cadenas de conidios.",
            "El color y la textura colonial cambian con el medio, la temperatura, el tiempo y las condiciones de captura.",
            "No se proponen especies y ninguna hipótesis sustituye la identificación del laboratorio.",
        ],
    }

    if quality_status == "rejected":
        return {
            **base,
            "status": "unavailable",
            "summary": (
                "No se genera una hipótesis taxonómica porque la captura no superó la puerta de calidad."
            ),
            "morphological_description": {
                "macroscopy": [],
                "microscopy": [],
            },
        }

    macro_description = _describe_macroscopy(petri)
    micro_description = _describe_microscopy(micro)
    macro_score = _macro_growth_index(petri)
    filament_score = _filament_index(micro)
    has_growth = _as_int(petri.get("region_count")) > 0 or _as_float(
        petri.get("colony_coverage")
    ) >= 0.008

    fungal_supported = predicted_label == PredictedLabel.PROBABLE_FUNGAL_GROWTH or (
        has_growth and filament_score >= 0.22
    )

    if not fungal_supported:
        return {
            **base,
            "status": "insufficient",
            "summary": (
                "Las mediciones actuales no sostienen un diferencial de género fúngico. "
                "Se conserva el resultado general y la revisión humana."
            ),
            "morphological_description": {
                "macroscopy": macro_description,
                "microscopy": micro_description,
            },
            "broad_interpretation": {
                "label": "Patrón fúngico filamentoso no demostrado",
                "compatibility_index": round(filament_score, 4),
            },
        }

    penicillium = _penicillium_candidate(petri, micro, macro_score, filament_score)
    aspergillus = _aspergillus_candidate(petri, micro, macro_score, filament_score)
    candidates = sorted(
        [penicillium, aspergillus],
        key=lambda item: item["compatibility_index"],
        reverse=True,
    )
    top = candidates[0]
    second = candidates[1]
    primary = None
    if (
        top["compatibility_index"] >= 0.30
        and top["compatibility_index"] - second["compatibility_index"] >= 0.03
    ):
        primary = top["id"]

    if primary == "penicillium_like":
        summary = (
            "Las imágenes son compatibles con crecimiento fúngico filamentoso. "
            "La morfología tipo Penicillium es una hipótesis posible, no confirmada; "
            "faltan estructuras reproductivas diagnósticas y validación molecular."
        )
    elif primary == "aspergillus_like":
        summary = (
            "Las imágenes son compatibles con crecimiento fúngico filamentoso. "
            "La morfología tipo Aspergillus es una hipótesis posible, no confirmada; "
            "no se ha demostrado una cabeza conidial ni una vesícula terminal."
        )
    else:
        summary = (
            "Las imágenes son compatibles con un hongo filamentoso, pero Penicillium-like y "
            "Aspergillus-like no pueden separarse con las estructuras visibles. El género "
            "permanece no concluyente."
        )

    return {
        **base,
        "status": "available",
        "summary": summary,
        "primary_hypothesis": primary,
        "morphological_description": {
            "macroscopy": macro_description,
            "microscopy": micro_description,
        },
        "broad_interpretation": {
            "label": "Compatible con hongo filamentoso",
            "compatibility_index": round(
                _clip01(0.48 * macro_score + 0.52 * filament_score),
                4,
            ),
        },
        "candidates": candidates,
    }


def _penicillium_candidate(
    petri: dict,
    micro: dict,
    macro_score: float,
    filament_score: float,
) -> dict:
    hue = _as_float(petri.get("mean_hue"))
    saturation = _as_float(petri.get("mean_saturation"))
    texture = _as_float(petri.get("mean_texture_std"))
    branch_density = _as_float(micro.get("branch_point_density"))
    elongated = _as_float(micro.get("elongated_component_ratio"))

    green_support = _green_colour_support(hue, saturation)
    texture_support = _clip01(texture / 35.0)
    branch_support = _clip01(branch_density / 0.0015)
    elongation_support = _clip01(elongated / 0.45)
    score = min(
        _MAX_GENUS_COMPATIBILITY,
        0.08
        + 0.14 * macro_score
        + 0.16 * filament_score
        + 0.07 * green_support
        + 0.025 * texture_support
        + 0.025 * branch_support
        + 0.015 * elongation_support,
    )

    supporting: list[str] = []
    if macro_score >= 0.35:
        supporting.append("Crecimiento colonial macroscópico claramente visible.")
    if green_support >= 0.45:
        supporting.append("Tonalidad colonial media compatible con una gama gris-verdosa o verde-azulada.")
    if texture_support >= 0.45:
        supporting.append("Variación de textura colonial compatible con una superficie heterogénea o esporulada.")
    if filament_score >= 0.25:
        supporting.append("La microscopía contiene estructuras lineales compatibles con hifas o micelio.")
    if branch_support >= 0.30:
        supporting.append("Se detectó ramificación microscópica, rasgo necesario pero no específico.")

    return {
        "id": "penicillium_like",
        "display_name": "Morfología tipo Penicillium",
        "compatibility_index": round(score, 4),
        "compatibility_label": _compatibility_label(score),
        "supporting_evidence": supporting,
        "missing_or_contradictory_evidence": [
            "No se ha reconocido un penicilo o conidióforo ramificado de forma semántica.",
            "No se han demostrado métulas, fiálides ni cadenas de conidios.",
            "No se conoce todavía el patrón mono-, bi-, ter- o quaterverticilado.",
        ],
        "required_confirmation": [
            "Preparación microscópica que muestre conidióforos maduros y cadenas de conidios.",
            "Comparación en medios y condiciones de incubación estandarizados.",
            "Secuenciación ITS y marcador secundario, preferentemente BenA para resolución dentro de Penicillium.",
        ],
    }


def _aspergillus_candidate(
    petri: dict,
    micro: dict,
    macro_score: float,
    filament_score: float,
) -> dict:
    branch_density = _as_float(micro.get("branch_point_density"))
    round_density = _as_float(micro.get("round_component_density"))
    elongated = _as_float(micro.get("elongated_component_ratio"))
    branch_support = _clip01(branch_density / 0.0015)
    round_support = _clip01(round_density / 0.0012)
    elongation_support = _clip01(elongated / 0.45)
    score = min(
        _MAX_GENUS_COMPATIBILITY,
        0.07
        + 0.12 * macro_score
        + 0.15 * filament_score
        + 0.035 * branch_support
        + 0.035 * round_support
        + 0.015 * elongation_support,
    )

    supporting: list[str] = []
    if macro_score >= 0.35:
        supporting.append("Crecimiento colonial macroscópico claramente visible.")
    if filament_score >= 0.25:
        supporting.append("La microscopía contiene estructuras lineales compatibles con hifas o micelio.")
    if branch_support >= 0.30:
        supporting.append("Se detectó ramificación microscópica, aunque no es específica de Aspergillus.")
    if round_support >= 0.30:
        supporting.append("Se observaron componentes redondeados que requieren revisión como posibles estructuras reproductivas o artefactos.")

    return {
        "id": "aspergillus_like",
        "display_name": "Morfología tipo Aspergillus",
        "compatibility_index": round(score, 4),
        "compatibility_label": _compatibility_label(score),
        "supporting_evidence": supporting,
        "missing_or_contradictory_evidence": [
            "No se ha reconocido una vesícula terminal de forma semántica.",
            "No se ha demostrado una cabeza conidial radiada o columnar.",
            "No se ha determinado si las fiálides son uniseriadas o biseriadas.",
        ],
        "required_confirmation": [
            "Preparación microscópica que muestre la unión entre estipe, vesícula, métulas/fiálides y conidios.",
            "Caracterización colonial en medios y temperaturas estandarizados.",
            "Secuenciación ITS y marcador secundario apropiado, como CaM o BenA según el grupo.",
        ],
    }


def _describe_macroscopy(petri: dict) -> list[str]:
    descriptions: list[str] = []
    region_count = _as_int(petri.get("region_count"))
    coverage = _as_float(petri.get("colony_coverage"))
    hue = _as_float(petri.get("mean_hue"))
    saturation = _as_float(petri.get("mean_saturation"))
    intensity = _as_float(petri.get("mean_intensity"))
    texture = _as_float(petri.get("mean_texture_std"))
    circularity = _as_float(petri.get("mean_circularity"))
    irregularity = _as_float(petri.get("edge_irregularity"))

    if region_count > 0:
        descriptions.append(
            f"{region_count} región(es) coloniales candidatas, con cobertura aproximada de {coverage:.1%}."
        )
    descriptions.append(_colour_description(hue, saturation, intensity))
    if texture >= 24:
        descriptions.append("Textura visual marcadamente heterogénea; podría corresponder a micelio aéreo o esporulación, pero requiere inspección directa.")
    elif texture >= 12:
        descriptions.append("Textura visual moderadamente heterogénea.")
    else:
        descriptions.append("Textura visual relativamente uniforme en las regiones segmentadas.")
    if irregularity >= 0.42:
        descriptions.append("Márgenes predominantemente irregulares o lobulados.")
    elif circularity >= 0.62:
        descriptions.append("Regiones predominantemente circulares.")
    else:
        descriptions.append("Forma colonial intermedia, sin patrón geométrico dominante.")
    return descriptions


def _describe_microscopy(micro: dict) -> list[str]:
    descriptions: list[str] = []
    filament = _as_float(micro.get("filament_coverage"))
    branch = _as_float(micro.get("branch_point_density"))
    elongated = _as_float(micro.get("elongated_component_ratio"))
    round_density = _as_float(micro.get("round_component_density"))
    components = _as_int(micro.get("component_count"))

    if filament >= 0.08:
        descriptions.append(f"Cobertura filamentosa alta ({filament:.1%}) en el campo analizado.")
    elif filament >= 0.02:
        descriptions.append(f"Cobertura filamentosa detectable ({filament:.1%}) en el campo analizado.")
    else:
        descriptions.append("Cobertura filamentosa escasa o no demostrada.")
    if branch >= 0.001:
        descriptions.append("Ramificación microscópica frecuente, sin asignación semántica a conidióforos.")
    elif branch > 0:
        descriptions.append("Señales puntuales de ramificación microscópica.")
    if elongated >= 0.18:
        descriptions.append(f"Proporción relevante de componentes alargados ({elongated:.1%}).")
    if round_density >= 0.0005:
        descriptions.append("Se detectaron componentes redondeados; pueden representar células, conidios, burbujas o artefactos.")
    descriptions.append(f"{components} componente(s) estructurales fueron medidos antes de la poda visual.")
    return descriptions


def _macro_growth_index(petri: dict) -> float:
    coverage = _as_float(petri.get("colony_coverage"))
    regions = _as_int(petri.get("region_count"))
    texture = _as_float(petri.get("mean_texture_std"))
    irregularity = _as_float(petri.get("edge_irregularity"))
    saturation = _as_float(petri.get("mean_saturation"))
    return _clip01(
        0.34 * min(1.0, coverage / 0.25)
        + 0.18 * min(1.0, regions / 5.0)
        + 0.20 * min(1.0, texture / 35.0)
        + 0.16 * min(1.0, irregularity / 0.55)
        + 0.12 * min(1.0, saturation / 0.45)
    )


def _filament_index(micro: dict) -> float:
    edge = _as_float(micro.get("edge_density"))
    filament = _as_float(micro.get("filament_coverage"))
    skeleton = _as_float(micro.get("skeleton_density"))
    branch = _as_float(micro.get("branch_point_density"))
    elongated = _as_float(micro.get("elongated_component_ratio"))
    return _clip01(
        0.22 * min(1.0, edge / 0.14)
        + 0.28 * min(1.0, filament / 0.12)
        + 0.14 * min(1.0, skeleton / 0.05)
        + 0.20 * min(1.0, branch / 0.0015)
        + 0.16 * min(1.0, elongated / 0.45)
    )


def _green_colour_support(hue: float, saturation: float) -> float:
    if saturation < 0.06:
        return 0.20
    if 0.22 <= hue <= 0.50:
        centre = 0.36
        distance = abs(hue - centre) / 0.14
        return _clip01((1.0 - distance) * min(1.0, saturation / 0.35) + 0.25)
    return 0.0


def _colour_description(hue: float, saturation: float, intensity: float) -> str:
    brightness = "oscura" if intensity < 85 else "clara" if intensity > 180 else "media"
    if saturation < 0.08:
        colour = "grisácea o poco saturada"
    elif 0.18 <= hue < 0.25:
        colour = "amarillenta u olivácea"
    elif 0.25 <= hue <= 0.50:
        colour = "verdosa a verde-azulada"
    elif 0.50 < hue <= 0.72:
        colour = "azulada o violácea"
    elif hue < 0.08 or hue > 0.95:
        colour = "rojiza"
    else:
        colour = "cromáticamente mixta"
    return f"Tonalidad colonial media {colour}, con luminosidad {brightness}."


def _compatibility_label(score: float) -> str:
    if score >= 0.36:
        return "posible, no confirmada"
    if score >= 0.26:
        return "evidencia limitada"
    return "soporte bajo"


def _record(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _as_float(value: Any) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _as_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    return 0


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, value))
