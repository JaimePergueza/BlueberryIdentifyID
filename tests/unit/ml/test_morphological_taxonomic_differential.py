from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.ml.inference_engine.morphological_taxonomic_differential import (
    DIFFERENTIAL_ENGINE_NAME,
    DIFFERENTIAL_ENGINE_VERSION,
    build_taxonomic_differential,
)


def _fungal_features() -> dict:
    return {
        "petri": {
            "region_count": 4,
            "colony_coverage": 0.42,
            "mean_texture_std": 31.0,
            "edge_irregularity": 0.48,
            "mean_circularity": 0.52,
            "mean_saturation": 0.24,
            "mean_hue": 0.34,
            "mean_intensity": 112.0,
        },
        "micro": {
            "edge_density": 0.09,
            "filament_coverage": 0.085,
            "skeleton_density": 0.035,
            "branch_point_density": 0.0012,
            "elongated_component_ratio": 0.34,
            "round_component_density": 0.0003,
            "component_count": 76,
        },
    }


def test_builds_limited_penicillium_like_hypothesis_for_filamentous_pattern() -> None:
    result = build_taxonomic_differential(
        predicted_label=PredictedLabel.PROBABLE_FUNGAL_GROWTH,
        feature_summary=_fungal_features(),
        quality_summary={"overall_status": "accepted"},
    )

    assert result["status"] == "available"
    assert result["engine"] == {
        "name": DIFFERENTIAL_ENGINE_NAME,
        "version": DIFFERENTIAL_ENGINE_VERSION,
    }
    assert result["primary_hypothesis"] == "penicillium_like"
    assert "Penicillium" in result["summary"]
    assert "no confirmada" in result["summary"]

    candidates = {candidate["id"]: candidate for candidate in result["candidates"]}
    assert set(candidates) == {"penicillium_like", "aspergillus_like"}
    assert candidates["penicillium_like"]["compatibility_index"] <= 0.49
    assert candidates["aspergillus_like"]["compatibility_index"] <= 0.49
    assert any(
        "fiálides" in item
        for item in candidates["penicillium_like"]["missing_or_contradictory_evidence"]
    )
    assert all("especie" not in candidate["display_name"].lower() for candidate in candidates.values())


def test_rejected_capture_never_emits_genus_hypotheses() -> None:
    result = build_taxonomic_differential(
        predicted_label=PredictedLabel.PROBABLE_FUNGAL_GROWTH,
        feature_summary=_fungal_features(),
        quality_summary={"overall_status": "rejected"},
    )

    assert result["status"] == "unavailable"
    assert result["primary_hypothesis"] is None
    assert result["candidates"] == []
    assert "puerta de calidad" in result["summary"]


def test_non_filamentous_pattern_keeps_taxonomic_differential_insufficient() -> None:
    features = _fungal_features()
    features["micro"] = {
        "edge_density": 0.01,
        "filament_coverage": 0.002,
        "skeleton_density": 0.001,
        "branch_point_density": 0.0,
        "elongated_component_ratio": 0.02,
        "round_component_density": 0.0008,
        "component_count": 12,
    }

    result = build_taxonomic_differential(
        predicted_label=PredictedLabel.PROBABLE_BACTERIAL_GROWTH,
        feature_summary=features,
        quality_summary={"overall_status": "accepted"},
    )

    assert result["status"] == "insufficient"
    assert result["primary_hypothesis"] is None
    assert result["candidates"] == []
    assert result["broad_interpretation"]["label"] == "Patrón fúngico filamentoso no demostrado"


def test_ambiguous_genus_scores_do_not_force_a_primary_genus() -> None:
    features = _fungal_features()
    features["petri"]["mean_hue"] = 0.75
    features["petri"]["mean_saturation"] = 0.04
    features["micro"]["branch_point_density"] = 0.0008
    features["micro"]["round_component_density"] = 0.0012

    result = build_taxonomic_differential(
        predicted_label=PredictedLabel.PROBABLE_FUNGAL_GROWTH,
        feature_summary=features,
        quality_summary={"overall_status": "warning"},
    )

    assert result["status"] == "available"
    assert result["primary_hypothesis"] is None
    assert "no pueden separarse" in result["summary"]
