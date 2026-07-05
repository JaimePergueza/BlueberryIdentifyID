"""Unit tests for PreliminaryTwoImageAnalysisEngine."""

from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.ml.inference_engine.preliminary_two_image_analysis_engine import (
    PRELIMINARY_DISCLAIMER,
    PreliminaryTwoImageAnalysisEngine,
)


def _engine():
    return PreliminaryTwoImageAnalysisEngine()


def test_returns_a_valid_label():
    result = _engine().analyze(petri_image_bytes=b"fake", micro_image_bytes=b"fake")
    assert result.predicted_label in list(PredictedLabel)


def test_disclaimer_is_non_empty():
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
    expected = {lbl.value for lbl in PredictedLabel}
    assert set(result.class_probabilities.keys()) == expected


def test_requires_human_review_always_true():
    # Fase 40.1: all preliminary uploads require expert review regardless of label.
    result = _engine().analyze(petri_image_bytes=b"x", micro_image_bytes=b"y")
    assert result.requires_human_review is True


def test_upload_id_is_non_empty_string():
    result = _engine().analyze(petri_image_bytes=b"x", micro_image_bytes=b"y")
    assert isinstance(result.upload_id, str)
    assert len(result.upload_id) > 0


def test_upload_id_changes_each_call():
    engine = _engine()
    r1 = engine.analyze(petri_image_bytes=b"x", micro_image_bytes=b"y")
    r2 = engine.analyze(petri_image_bytes=b"x", micro_image_bytes=b"y")
    assert r1.upload_id != r2.upload_id
