"""Conservative, explainable morphology-based differential for blueberry samples.

The module never identifies a genus or species. It compares broad visual
measurements with morphology profiles reported in blueberry pathology and
postharvest literature. Compatibility scores are deliberately capped below
50 %, are not calibrated probabilities, and require expert/molecular review.
"""

from __future__ import annotations

from typing import Any, Callable

from blueberry_microid.domain.enums.predicted_label import PredictedLabel

DIFFERENTIAL_ENGINE_NAME = "MorphologicalDifferentialEngine"
DIFFERENTIAL_ENGINE_VERSION = "0.2.0"
_MAX_COMPATIBILITY = 0.49


def build_taxonomic_differential(
    *,
    predicted_label: PredictedLabel,
    feature_summary: dict | None,
    quality_summary: dict | None,
) -> dict:
    features = _record(feature_summary)
    quality = _record(quality_summary)
    petri = _record(features.get("petri"))
    micro = _record(features.get("micro"))
    quality_status = str(quality.get("overall_status") or "unknown")

    base = {
        "engine": {"name": DIFFERENTIAL_ENGINE_NAME, "version": DIFFERENTIAL_ENGINE_VERSION},
        "scope": "diferencial morfológico visual orientado a microorganismos asociados con arándanos",
        "score_semantics": (
            "Los índices son compatibilidades heurísticas no calibradas. No son probabilidades "
            "científicas ni identificaciones taxonómicas."
        ),
        "primary_hypothesis": None,
        "candidates": [],
        "confirmation_required": [
            "Revisión de varios campos microscópicos maduros por un especialista.",
            "Registrar medio, temperatura, tiempo, aumento, microscopio y tinción o montaje.",
            "Confirmación molecular con ITS y marcadores secundarios apropiados al grupo.",
        ],
        "limitations": [
            "No se reconocen todavía estructuras reproductivas de forma semántica.",
            "La morfología cambia con medio, temperatura, edad del cultivo y captura.",
            "Las especies citadas son ejemplos reportados en arándanos, no resultados del análisis.",
            "Ninguna hipótesis sustituye aislamiento puro, revisión experta o confirmación molecular.",
        ],
    }

    if quality_status == "rejected":
        return {
            **base,
            "status": "unavailable",
            "summary": "No se genera un diferencial porque la captura no superó la puerta de calidad.",
            "morphological_description": {"macroscopy": [], "microscopy": []},
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
    broad_index = _clip01(0.48 * macro_score + 0.52 * filament_score)

    if not fungal_supported:
        return {
            **base,
            "status": "insufficient",
            "summary": (
                "Las mediciones actuales no sostienen un diferencial de hongos filamentosos. "
                "Se conserva la categoría general y la revisión humana."
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

    builders: tuple[Callable[[dict, dict, float, float], dict], ...] = (
        _penicillium_candidate,
        _aspergillus_candidate,
        _botrytis_candidate,
        _colletotrichum_candidate,
        _alternaria_candidate,
        _fusarium_candidate,
        _mucorales_candidate,
    )
    candidates = sorted(
        [builder(petri, micro, macro_score, filament_score) for builder in builders],
        key=lambda item: item["compatibility_index"],
        reverse=True,
    )
    top = candidates[0]
    second = candidates[1]
    primary = None
    if top["compatibility_index"] >= 0.34 and (
        top["compatibility_index"] - second["compatibility_index"] >= 0.04
    ):
        primary = top["id"]

    if primary:
        summary = (
            "Las imágenes son compatibles con crecimiento fúngico filamentoso. "
            f"La hipótesis visual principal es {top['display_name']}, pero no está confirmada "
            "y debe compararse con las demás posibilidades y con estructuras diagnósticas."
        )
    else:
        summary = (
            "Las imágenes son compatibles con un hongo filamentoso, pero los perfiles visuales "
            "considerados para arándanos se superponen. El género permanece no concluyente."
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
            "compatibility_index": round(broad_index, 4),
        },
        "candidates": candidates,
    }


def _candidate(
    *,
    identifier: str,
    name: str,
    examples: list[str],
    score: float,
    supporting: list[str],
    missing: list[str],
    confirmation: list[str],
) -> dict:
    bounded = min(_MAX_COMPATIBILITY, max(0.0, score))
    return {
        "id": identifier,
        "display_name": name,
        "reported_blueberry_examples": examples,
        "compatibility_index": round(bounded, 4),
        "compatibility_label": _compatibility_label(bounded),
        "supporting_evidence": supporting,
        "missing_or_contradictory_evidence": missing,
        "required_confirmation": confirmation,
    }


def _shared(petri: dict, micro: dict) -> dict[str, float]:
    return {
        "hue": _as_float(petri.get("mean_hue")),
        "saturation": _as_float(petri.get("mean_saturation")),
        "intensity": _as_float(petri.get("mean_intensity")),
        "texture": _clip01(_as_float(petri.get("mean_texture_std")) / 35.0),
        "irregularity": _clip01(_as_float(petri.get("edge_irregularity")) / 0.55),
        "circularity": _clip01(_as_float(petri.get("mean_circularity"))),
        "branch": _clip01(_as_float(micro.get("branch_point_density")) / 0.0015),
        "round": _clip01(_as_float(micro.get("round_component_density")) / 0.0012),
        "elongated": _clip01(_as_float(micro.get("elongated_component_ratio")) / 0.45),
    }


def _penicillium_candidate(petri: dict, micro: dict, macro: float, filament: float) -> dict:
    s = _shared(petri, micro)
    green = _green_colour_support(s["hue"], s["saturation"])
    score = 0.07 + 0.12 * macro + 0.13 * filament + 0.07 * green + 0.04 * s["texture"] + 0.03 * s["branch"]
    support = _common_support(macro, filament)
    if green >= 0.45:
        support.append("Tonalidad gris-verdosa o verde-azulada compatible con colonias esporuladas.")
    if s["texture"] >= 0.45:
        support.append("Textura colonial heterogénea o pulverulenta aparente.")
    return _candidate(
        identifier="penicillium_like",
        name="Morfología tipo Penicillium",
        examples=["Penicillium expansum", "Penicillium crustosum"],
        score=score,
        supporting=support,
        missing=[
            "No se reconoció un penicilo ramificado de forma semántica.",
            "No se demostraron métulas, fiálides ni cadenas de conidios.",
        ],
        confirmation=["Conidióforos maduros en montaje adecuado.", "ITS y BenA u otro marcador secundario."],
    )


def _aspergillus_candidate(petri: dict, micro: dict, macro: float, filament: float) -> dict:
    s = _shared(petri, micro)
    score = 0.06 + 0.11 * macro + 0.12 * filament + 0.05 * s["round"] + 0.04 * s["branch"] + 0.02 * s["texture"]
    support = _common_support(macro, filament)
    if s["round"] >= 0.30:
        support.append("Componentes redondeados que deben revisarse como posibles estructuras reproductivas o artefactos.")
    return _candidate(
        identifier="aspergillus_like",
        name="Morfología tipo Aspergillus",
        examples=["Aspergillus tubingensis", "Aspergillus sección Nigri"],
        score=score,
        supporting=support,
        missing=["No se reconoció vesícula terminal.", "No se demostró cabeza conidial radiada o columnar."],
        confirmation=["Mostrar continuidad entre estipe, vesícula, fiálides y conidios.", "ITS y CaM/BenA según el grupo."],
    )


def _botrytis_candidate(petri: dict, micro: dict, macro: float, filament: float) -> dict:
    s = _shared(petri, micro)
    gray = _clip01((0.20 - min(0.20, s["saturation"])) / 0.20)
    score = 0.06 + 0.13 * macro + 0.14 * filament + 0.05 * gray + 0.04 * s["texture"] + 0.03 * s["branch"] + 0.02 * s["irregularity"]
    support = _common_support(macro, filament)
    if gray >= 0.45:
        support.append("Coloración grisácea o poco saturada compatible con moho gris.")
    if s["texture"] >= 0.45:
        support.append("Superficie visualmente aérea o heterogénea.")
    return _candidate(
        identifier="botrytis_like",
        name="Morfología tipo Botrytis",
        examples=["Botrytis cinerea"],
        score=score,
        supporting=support,
        missing=["No se reconocieron conidióforos botrioides.", "No se demostraron racimos de conidios ni esclerocios."],
        confirmation=["Microscopía de estructuras fértiles.", "ITS y marcadores como G3PDH/HSP60/RPB2 cuando corresponda."],
    )


def _colletotrichum_candidate(petri: dict, micro: dict, macro: float, filament: float) -> dict:
    s = _shared(petri, micro)
    pigmented = _clip01((140.0 - min(140.0, s["intensity"])) / 80.0)
    score = 0.05 + 0.12 * macro + 0.11 * filament + 0.04 * s["circularity"] + 0.04 * pigmented + 0.03 * s["round"] + 0.02 * s["texture"]
    support = _common_support(macro, filament)
    if s["circularity"] >= 0.55:
        support.append("Regiones relativamente circulares o concéntricas.")
    if pigmented >= 0.35:
        support.append("Áreas oscuras que requieren revisión como pigmentación o acérvulos.")
    return _candidate(
        identifier="colletotrichum_like",
        name="Morfología tipo Colletotrichum",
        examples=["Colletotrichum acutatum species complex", "Colletotrichum gloeosporioides species complex"],
        score=score,
        supporting=support,
        missing=["No se reconocieron acérvulos, setas ni conidios falcados/cilíndricos.", "No se evaluaron apresorios."],
        confirmation=["Cultivo y montaje de conidios/apresorios.", "Análisis multilocus; ITS solo suele ser insuficiente."],
    )


def _alternaria_candidate(petri: dict, micro: dict, macro: float, filament: float) -> dict:
    s = _shared(petri, micro)
    olive = _clip01(0.6 * _green_colour_support(s["hue"], s["saturation"]) + 0.4 * _clip01((150.0 - s["intensity"]) / 100.0))
    score = 0.05 + 0.12 * macro + 0.11 * filament + 0.06 * olive + 0.04 * s["texture"] + 0.03 * s["irregularity"] + 0.02 * s["elongated"]
    support = _common_support(macro, filament)
    if olive >= 0.40:
        support.append("Tonalidad oscura u olivácea compatible con hongos dematiáceos.")
    return _candidate(
        identifier="alternaria_like",
        name="Morfología tipo Alternaria",
        examples=["Alternaria alternata species group"],
        score=score,
        supporting=support,
        missing=["No se reconocieron conidios muriformes ni cadenas acropétalas.", "No se demostró pico conidial."],
        confirmation=["Montaje de conidios maduros.", "Secuenciación multilocus según el grupo Alternaria."],
    )


def _fusarium_candidate(petri: dict, micro: dict, macro: float, filament: float) -> dict:
    s = _shared(petri, micro)
    pale = _clip01((s["intensity"] - 100.0) / 100.0)
    score = 0.05 + 0.11 * macro + 0.14 * filament + 0.05 * s["elongated"] + 0.04 * pale + 0.02 * s["branch"] + 0.02 * s["texture"]
    support = _common_support(macro, filament)
    if s["elongated"] >= 0.35:
        support.append("Proporción importante de estructuras alargadas.")
    if pale >= 0.35:
        support.append("Colonias claras o poco pigmentadas en la captura.")
    return _candidate(
        identifier="fusarium_like",
        name="Morfología tipo Fusarium",
        examples=["Fusarium oxysporum species complex", "Fusarium verticillioides"],
        score=score,
        supporting=support,
        missing=["No se reconocieron macroconidios falcados, microconidios ni clamidosporas.", "No se evaluó la célula basal de los macroconidios."],
        confirmation=["Montaje de macro/microconidios maduros.", "TEF1-α y RPB2 u otros marcadores del complejo."],
    )


def _mucorales_candidate(petri: dict, micro: dict, macro: float, filament: float) -> dict:
    s = _shared(petri, micro)
    low_branch = 1.0 - s["branch"]
    score = 0.04 + 0.12 * macro + 0.15 * filament + 0.05 * s["elongated"] + 0.04 * low_branch + 0.03 * _clip01(_as_float(petri.get("colony_coverage")) / 0.30)
    support = _common_support(macro, filament)
    if s["elongated"] >= 0.40:
        support.append("Estructuras largas y continuas con ramificación limitada en la detección.")
    return _candidate(
        identifier="mucorales_like",
        name="Morfología tipo Mucorales/Rhizopus",
        examples=["Rhizopus spp.", "Mucor spp."],
        score=score,
        supporting=support,
        missing=["No se reconocieron esporangios, columelas, rizoides ni estolones.", "No se determinó septación real de las hifas."],
        confirmation=["Campo que muestre esporangióforos y estructuras de anclaje.", "ITS y marcadores apropiados para Mucorales."],
    )


def _common_support(macro: float, filament: float) -> list[str]:
    items: list[str] = []
    if macro >= 0.35:
        items.append("Crecimiento colonial macroscópico claramente visible.")
    if filament >= 0.25:
        items.append("Estructuras lineales compatibles con hifas o micelio.")
    return items


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
        descriptions.append(f"{region_count} región(es) candidatas, con cobertura aproximada de {coverage:.1%}.")
    descriptions.append(_colour_description(hue, saturation, intensity))
    if texture >= 24:
        descriptions.append("Textura visual marcadamente heterogénea; puede corresponder a micelio aéreo o esporulación.")
    elif texture >= 12:
        descriptions.append("Textura visual moderadamente heterogénea.")
    else:
        descriptions.append("Textura visual relativamente uniforme.")
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
    if filament >= 0.16:
        descriptions.append(f"Cobertura filamentosa alta ({filament:.1%}) en el campo analizado.")
    elif filament >= 0.06:
        descriptions.append(f"Cobertura filamentosa moderada ({filament:.1%}) en el campo analizado.")
    elif filament >= 0.02:
        descriptions.append(f"Cobertura filamentosa limitada pero detectable ({filament:.1%}).")
    else:
        descriptions.append("Cobertura filamentosa escasa o no demostrada.")
    if branch >= 0.001:
        descriptions.append("Ramificación microscópica frecuente, todavía sin asignación semántica.")
    elif branch > 0:
        descriptions.append("Señales puntuales de ramificación microscópica.")
    if elongated >= 0.18:
        descriptions.append(f"Proporción relevante de componentes alargados ({elongated:.1%}).")
    if round_density >= 0.0005:
        descriptions.append("Componentes redondeados presentes; pueden ser células, conidios, burbujas o artefactos.")
    descriptions.append(f"{components} componente(s) estructurales medidos antes de la poda visual.")
    return descriptions


def _macro_growth_index(petri: dict) -> float:
    return _clip01(
        0.34 * min(1.0, _as_float(petri.get("colony_coverage")) / 0.25)
        + 0.18 * min(1.0, _as_int(petri.get("region_count")) / 5.0)
        + 0.20 * min(1.0, _as_float(petri.get("mean_texture_std")) / 35.0)
        + 0.16 * min(1.0, _as_float(petri.get("edge_irregularity")) / 0.55)
        + 0.12 * min(1.0, _as_float(petri.get("mean_saturation")) / 0.45)
    )


def _filament_index(micro: dict) -> float:
    return _clip01(
        0.22 * min(1.0, _as_float(micro.get("edge_density")) / 0.14)
        + 0.28 * min(1.0, _as_float(micro.get("filament_coverage")) / 0.12)
        + 0.14 * min(1.0, _as_float(micro.get("skeleton_density")) / 0.05)
        + 0.20 * min(1.0, _as_float(micro.get("branch_point_density")) / 0.0015)
        + 0.16 * min(1.0, _as_float(micro.get("elongated_component_ratio")) / 0.45)
    )


def _green_colour_support(hue: float, saturation: float) -> float:
    if saturation < 0.06:
        return 0.20
    if 0.22 <= hue <= 0.50:
        distance = abs(hue - 0.36) / 0.14
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
    if score >= 0.38:
        return "posible, no confirmada"
    if score >= 0.28:
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
