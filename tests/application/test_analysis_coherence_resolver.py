from blueberry_microid.application.services.analysis_coherence_resolver import (
    resolve_analysis_coherence,
)
from blueberry_microid.domain.enums.predicted_label import PredictedLabel


def _features(broad_index: float = 0.62):
    return {
        "petri": {
            "colony_coverage": 0.56,
            "plate_detected": True,
            "segmentation_conflict": False,
        },
        "micro": {
            "filament_coverage": 0.098,
            "elongated_component_ratio": 0.10,
            "branch_point_density": 0.0001,
            "field_detected": True,
        },
        "taxonomic_differential": {
            "status": "available",
            "broad_interpretation": {
                "label": "Compatible con hongo filamentoso",
                "compatibility_index": broad_index,
            },
        },
    }


def test_bacterial_label_with_substantial_filamentous_evidence_abstains():
    result = resolve_analysis_coherence(
        predicted_label=PredictedLabel.PROBABLE_BACTERIAL_GROWTH,
        confidence_score=0.583,
        class_scores={
            "probable_bacterial_growth": 0.583,
            "probable_fungal_growth": 0.104,
            "inconclusive": 0.104,
            "suspicious_growth": 0.104,
            "no_evident_growth": 0.105,
        },
        explanation="Patrón celular denso.",
        feature_summary=_features(),
        quality_summary={"overall_status": "accepted", "quality_score": 1.0},
        metadata={},
    )

    assert result.predicted_label == PredictedLabel.INCONCLUSIVE
    assert result.confidence_score == 0.40
    assert result.assessment["status"] == "conflict"
    assert result.assessment["conflicts"][0]["type"] == "bacterial_vs_filamentous"
    assert result.class_scores["inconclusive"] == 0.42
    assert "contradictorias" in (result.explanation or "")


def test_coherent_fungal_result_keeps_label():
    result = resolve_analysis_coherence(
        predicted_label=PredictedLabel.PROBABLE_FUNGAL_GROWTH,
        confidence_score=0.61,
        class_scores={"probable_fungal_growth": 0.61, "inconclusive": 0.39},
        explanation="Patrón filamentoso.",
        feature_summary=_features(),
        quality_summary={"overall_status": "accepted", "quality_score": 0.9},
        metadata={"culture_medium": "PDA"},
    )

    assert result.predicted_label == PredictedLabel.PROBABLE_FUNGAL_GROWTH
    assert result.assessment["status"] == "coherent"


def test_complete_metadata_is_reported_as_sufficient():
    metadata = {
        "lot_code": "L-01",
        "origin": "Carchi",
        "collection_date": "2026-07-31",
        "culture_medium": "PDA",
        "incubation_temperature_c": 25.0,
        "incubation_time_hours": 168.0,
        "magnification": "400×",
        "microscope_type": "Campo claro",
        "staining_method": "Azul de lactofenol",
    }
    result = resolve_analysis_coherence(
        predicted_label=PredictedLabel.PROBABLE_FUNGAL_GROWTH,
        confidence_score=0.60,
        class_scores={"probable_fungal_growth": 0.60, "inconclusive": 0.40},
        explanation=None,
        feature_summary=_features(),
        quality_summary={"overall_status": "accepted", "quality_score": 0.9},
        metadata=metadata,
    )

    assert result.assessment["metadata"]["status"] == "sufficient"
    assert result.assessment["metadata"]["missing_fields"] == []
