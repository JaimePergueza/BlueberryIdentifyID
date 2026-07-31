"""Unit tests for PreliminaryTwoImageAnalysisEngine.

Tests cover the output contract, explainability fields, quality-gated
classification using synthetic signals, and graceful fallback on corrupted
input.
"""

from io import BytesIO

import numpy as np
from PIL import Image

from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.ml.inference_engine.micro_visual_signal_extractor import MicroVisualSignals
from blueberry_microid.ml.inference_engine.petri_visual_signal_extractor import PetriVisualSignals
from blueberry_microid.ml.inference_engine.preliminary_two_image_analysis_engine import (
    PRELIMINARY_DISCLAIMER,
    PreliminaryAnalysisOutput,
    PreliminaryTwoImageAnalysisEngine,
    _classify,
)


def _jpeg(color=(200, 200, 200), width: int = 64, height: int = 64) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (width, height), color=color).save(buf, format="JPEG")
    return buf.getvalue()


def _petri_with_dark_spot() -> bytes:
    arr = np.full((100, 100, 3), 210, dtype=np.uint8)
    arr[35:55, 35:55] = 20
    buf = BytesIO()
    Image.fromarray(arr).save(buf, format="JPEG")
    return buf.getvalue()


def _micro_noisy() -> bytes:
    rng = np.random.default_rng(7)
    arr = rng.integers(0, 256, (64, 64, 3), dtype=np.uint8)
    buf = BytesIO()
    Image.fromarray(arr).save(buf, format="JPEG")
    return buf.getvalue()


def _engine() -> PreliminaryTwoImageAnalysisEngine:
    return PreliminaryTwoImageAnalysisEngine()


def _accepted_quality() -> dict:
    return {
        "overall_status": "accepted",
        "quality_score": 1.0,
        "blocking_reasons": [],
        "warning_reasons": [],
    }


def test_returns_preliminary_analysis_output():
    result = _engine().analyze(petri_image_bytes=b"bad", micro_image_bytes=b"bad")
    assert isinstance(result, PreliminaryAnalysisOutput)


def test_returns_a_valid_label():
    result = _engine().analyze(petri_image_bytes=b"fake", micro_image_bytes=b"fake")
    assert result.predicted_label in list(PredictedLabel)


def test_disclaimer_equals_constant():
    result = _engine().analyze(petri_image_bytes=b"", micro_image_bytes=b"")
    assert result.disclaimer == PRELIMINARY_DISCLAIMER


def test_confidence_score_in_range():
    result = _engine().analyze(petri_image_bytes=b"x", micro_image_bytes=b"y")
    assert 0.0 < result.confidence_score <= 1.0


def test_class_probabilities_sum_to_one():
    result = _engine().analyze(petri_image_bytes=b"x", micro_image_bytes=b"y")
    total = sum(result.class_probabilities.values())
    assert abs(total - 1.0) < 0.01


def test_class_probabilities_cover_all_labels():
    result = _engine().analyze(petri_image_bytes=b"x", micro_image_bytes=b"y")
    expected = {label.value for label in PredictedLabel}
    assert set(result.class_probabilities.keys()) == expected


def test_requires_human_review_always_true():
    result = _engine().analyze(petri_image_bytes=b"x", micro_image_bytes=b"y")
    assert result.requires_human_review is True


def test_upload_id_is_non_empty_string():
    result = _engine().analyze(petri_image_bytes=b"x", micro_image_bytes=b"y")
    assert isinstance(result.upload_id, str)
    assert result.upload_id


def test_upload_id_changes_each_call():
    engine = _engine()
    first = engine.analyze(petri_image_bytes=b"x", micro_image_bytes=b"y")
    second = engine.analyze(petri_image_bytes=b"x", micro_image_bytes=b"y")
    assert first.upload_id != second.upload_id


def test_explanation_is_non_empty_string_for_valid_images():
    result = _engine().analyze(petri_image_bytes=_jpeg(), micro_image_bytes=_jpeg())
    assert isinstance(result.explanation, str)
    assert result.explanation


def test_feature_summary_has_petri_and_micro_keys():
    result = _engine().analyze(petri_image_bytes=_jpeg(), micro_image_bytes=_jpeg())
    assert result.feature_summary is not None
    assert "petri" in result.feature_summary
    assert "micro" in result.feature_summary


def test_feature_summary_petri_has_expected_keys():
    result = _engine().analyze(petri_image_bytes=_jpeg(), micro_image_bytes=_jpeg())
    petri = result.feature_summary["petri"]
    for key in ("region_count", "colony_coverage", "mean_saturation", "sharpness", "visualization"):
        assert key in petri, f"Missing key '{key}' in feature_summary.petri"


def test_feature_summary_micro_has_expected_keys():
    result = _engine().analyze(petri_image_bytes=_jpeg(), micro_image_bytes=_jpeg())
    micro = result.feature_summary["micro"]
    for key in ("mean_intensity", "intensity_std", "edge_density", "sharpness", "visualization"):
        assert key in micro, f"Missing key '{key}' in feature_summary.micro"


def test_quality_summary_has_expected_keys():
    result = _engine().analyze(petri_image_bytes=_jpeg(), micro_image_bytes=_jpeg())
    summary = result.quality_summary
    assert summary is not None
    for key in (
        "overall_status",
        "quality_score",
        "blocking_reasons",
        "warning_reasons",
        "petri_is_sharp",
        "micro_is_sharp",
        "petri_overexposed",
        "petri_underexposed",
        "micro_appears_empty",
    ):
        assert key in summary, f"Missing key '{key}' in quality_summary"


def test_decision_trace_is_non_empty_list():
    result = _engine().analyze(petri_image_bytes=_jpeg(), micro_image_bytes=_jpeg())
    assert isinstance(result.decision_trace, list)
    assert len(result.decision_trace) >= 3


def test_decision_trace_contains_label_assigned_step():
    result = _engine().analyze(petri_image_bytes=_jpeg(), micro_image_bytes=_jpeg())
    steps = [step.get("step") for step in result.decision_trace]
    assert "label_assigned" in steps


def test_decision_trace_label_assigned_matches_predicted_label():
    result = _engine().analyze(petri_image_bytes=_jpeg(), micro_image_bytes=_jpeg())
    assigned = next(step for step in result.decision_trace if step.get("step") == "label_assigned")
    assert assigned["label"] == result.predicted_label.value


def test_confidence_capped_below_mock_engine_max():
    result = _engine().analyze(petri_image_bytes=_jpeg(), micro_image_bytes=_jpeg())
    assert result.confidence_score <= 0.65


def test_corrupted_inputs_return_inconclusive_output():
    result = _engine().analyze(petri_image_bytes=b"junk", micro_image_bytes=b"garbage")
    assert result.predicted_label == PredictedLabel.INCONCLUSIVE
    assert result.quality_summary["overall_status"] == "rejected"
    assert result.requires_human_review is True


def test_corrupted_petri_warnings_propagated():
    result = _engine().analyze(petri_image_bytes=b"junk", micro_image_bytes=_jpeg())
    assert result.warnings is not None
    assert any("Petri" in warning for warning in result.warnings)


def test_corrupted_micro_warnings_propagated():
    result = _engine().analyze(petri_image_bytes=_jpeg(), micro_image_bytes=b"junk")
    assert result.warnings is not None
    assert any("Micro" in warning or "microsc" in warning.lower() for warning in result.warnings)


def _petri_no_growth() -> PetriVisualSignals:
    return PetriVisualSignals(
        region_count=0,
        colony_coverage=0.0,
        mean_saturation=0.0,
        mean_intensity=180.0,
        sharpness=500.0,
        extraction_ok=True,
        plate_detected=True,
    )


def _petri_with_growth(**kwargs) -> PetriVisualSignals:
    return PetriVisualSignals(
        region_count=3,
        colony_coverage=0.05,
        mean_saturation=0.2,
        mean_intensity=150.0,
        sharpness=400.0,
        extraction_ok=True,
        plate_detected=True,
        **kwargs,
    )


def _micro_empty() -> MicroVisualSignals:
    return MicroVisualSignals(
        mean_intensity=128.0,
        intensity_std=5.0,
        sharpness=40.0,
        edge_density=0.01,
        extraction_ok=True,
        field_detected=True,
    )


def _micro_structured(
    edge_density: float = 0.08,
    intensity_std: float = 30.0,
) -> MicroVisualSignals:
    return MicroVisualSignals(
        mean_intensity=128.0,
        intensity_std=intensity_std,
        sharpness=200.0,
        edge_density=edge_density,
        extraction_ok=True,
        field_detected=True,
    )


def test_classify_no_growth_when_no_petri_regions():
    label, _, _, _ = _classify(_petri_no_growth(), _micro_structured(), _accepted_quality())
    assert label == PredictedLabel.NO_EVIDENT_GROWTH


def test_classify_suspicious_when_petri_growth_but_low_micro_edges():
    label, _, _, _ = _classify(_petri_with_growth(), _micro_empty(), _accepted_quality())
    assert label == PredictedLabel.SUSPICIOUS_GROWTH


def test_classify_fungal_when_high_edge_density():
    label, _, _, _ = _classify(
        _petri_with_growth(),
        _micro_structured(edge_density=0.15),
        _accepted_quality(),
    )
    assert label == PredictedLabel.PROBABLE_FUNGAL_GROWTH


def test_classify_bacterial_when_moderate_edge_and_high_std():
    label, _, _, _ = _classify(
        _petri_with_growth(),
        _micro_structured(edge_density=0.07, intensity_std=25.0),
        _accepted_quality(),
    )
    assert label == PredictedLabel.PROBABLE_BACTERIAL_GROWTH


def test_classify_inconclusive_when_signals_ambiguous():
    label, _, _, _ = _classify(
        _petri_with_growth(),
        _micro_structured(edge_density=0.07, intensity_std=5.0),
        _accepted_quality(),
    )
    assert label == PredictedLabel.INCONCLUSIVE


def test_classify_returns_non_empty_explanation():
    _, _, explanation, _ = _classify(
        _petri_no_growth(),
        _micro_empty(),
        _accepted_quality(),
    )
    assert isinstance(explanation, str) and explanation


def test_classify_returns_non_empty_trace():
    _, _, _, trace = _classify(
        _petri_no_growth(),
        _micro_empty(),
        _accepted_quality(),
    )
    assert isinstance(trace, list) and trace


def test_no_growth_confidence_consistent():
    label, confidence, *_ = _classify(
        _petri_no_growth(),
        _micro_empty(),
        _accepted_quality(),
    )
    assert label == PredictedLabel.NO_EVIDENT_GROWTH
    assert 0.0 < confidence <= 0.65
