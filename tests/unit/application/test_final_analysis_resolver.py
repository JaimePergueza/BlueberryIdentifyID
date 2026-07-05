"""Unit tests for ResolveFinalAnalysisLabel (Fase 42).

Tests cover all five workflow outcomes: pending_human_review, human_confirmed,
human_corrected, inconclusive, rejected_invalid_sample.  No images, no DB,
no taxonomy, no training.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from blueberry_microid.application.services.final_analysis_resolver import (
    FINAL_STATUS_CONFIRMED,
    FINAL_STATUS_CORRECTED,
    FINAL_STATUS_INCONCLUSIVE,
    FINAL_STATUS_PENDING,
    FINAL_STATUS_REJECTED,
    FinalLabelResolution,
    resolve_final_label,
)
from blueberry_microid.domain.entities.human_review import HumanReview
from blueberry_microid.domain.entities.prediction import Prediction
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _prediction(label: PredictedLabel = PredictedLabel.SUSPICIOUS_GROWTH) -> Prediction:
    return Prediction(
        analysis_run_id=uuid4(),
        predicted_label=label,
        confidence_score=0.50,
        class_probabilities={l.value: 0.2 for l in PredictedLabel},
        requires_human_review=True,
        created_at=datetime.now(timezone.utc),
    )


def _review(
    decision: ReviewDecision,
    corrected_label: PredictedLabel | None = None,
) -> HumanReview:
    return HumanReview(
        analysis_run_id=uuid4(),
        reviewer_name="Dra. Lopez",
        review_decision=decision,
        corrected_label=corrected_label,
        is_final=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Return type
# ─────────────────────────────────────────────────────────────────────────────

def test_returns_final_label_resolution_instance():
    result = resolve_final_label(_prediction(), None)
    assert isinstance(result, FinalLabelResolution)


# ─────────────────────────────────────────────────────────────────────────────
# No review
# ─────────────────────────────────────────────────────────────────────────────

def test_no_review_status_is_pending():
    result = resolve_final_label(_prediction(), None)
    assert result.status == FINAL_STATUS_PENDING


def test_no_review_final_label_is_none():
    result = resolve_final_label(_prediction(), None)
    assert result.final_label is None


def test_no_review_human_review_completed_is_false():
    result = resolve_final_label(_prediction(), None)
    assert result.human_review_completed is False


# ─────────────────────────────────────────────────────────────────────────────
# confirmed
# ─────────────────────────────────────────────────────────────────────────────

def test_confirmed_status():
    result = resolve_final_label(
        _prediction(PredictedLabel.NO_EVIDENT_GROWTH),
        _review(ReviewDecision.CONFIRMED),
    )
    assert result.status == FINAL_STATUS_CONFIRMED


def test_confirmed_final_label_equals_predicted_label():
    pred = _prediction(PredictedLabel.PROBABLE_BACTERIAL_GROWTH)
    result = resolve_final_label(pred, _review(ReviewDecision.CONFIRMED))
    assert result.final_label == PredictedLabel.PROBABLE_BACTERIAL_GROWTH


def test_confirmed_human_review_completed_is_true():
    result = resolve_final_label(_prediction(), _review(ReviewDecision.CONFIRMED))
    assert result.human_review_completed is True


# ─────────────────────────────────────────────────────────────────────────────
# corrected
# ─────────────────────────────────────────────────────────────────────────────

def test_corrected_status():
    result = resolve_final_label(
        _prediction(),
        _review(ReviewDecision.CORRECTED, corrected_label=PredictedLabel.NO_EVIDENT_GROWTH),
    )
    assert result.status == FINAL_STATUS_CORRECTED


def test_corrected_final_label_equals_corrected_label():
    result = resolve_final_label(
        _prediction(PredictedLabel.SUSPICIOUS_GROWTH),
        _review(ReviewDecision.CORRECTED, corrected_label=PredictedLabel.PROBABLE_FUNGAL_GROWTH),
    )
    assert result.final_label == PredictedLabel.PROBABLE_FUNGAL_GROWTH


def test_corrected_does_not_use_prediction_label():
    """The corrected final_label must come from the review, not the prediction."""
    pred = _prediction(PredictedLabel.NO_EVIDENT_GROWTH)
    result = resolve_final_label(
        pred,
        _review(ReviewDecision.CORRECTED, corrected_label=PredictedLabel.PROBABLE_BACTERIAL_GROWTH),
    )
    assert result.final_label != pred.predicted_label


def test_corrected_human_review_completed_is_true():
    result = resolve_final_label(
        _prediction(),
        _review(ReviewDecision.CORRECTED, corrected_label=PredictedLabel.INCONCLUSIVE),
    )
    assert result.human_review_completed is True


# ─────────────────────────────────────────────────────────────────────────────
# marked_inconclusive
# ─────────────────────────────────────────────────────────────────────────────

def test_marked_inconclusive_status():
    result = resolve_final_label(_prediction(), _review(ReviewDecision.MARKED_INCONCLUSIVE))
    assert result.status == FINAL_STATUS_INCONCLUSIVE


def test_marked_inconclusive_final_label_is_inconclusive():
    result = resolve_final_label(_prediction(), _review(ReviewDecision.MARKED_INCONCLUSIVE))
    assert result.final_label == PredictedLabel.INCONCLUSIVE


def test_marked_inconclusive_human_review_completed_is_true():
    result = resolve_final_label(_prediction(), _review(ReviewDecision.MARKED_INCONCLUSIVE))
    assert result.human_review_completed is True


# ─────────────────────────────────────────────────────────────────────────────
# rejected_invalid_sample
# ─────────────────────────────────────────────────────────────────────────────

def test_rejected_status():
    result = resolve_final_label(_prediction(), _review(ReviewDecision.REJECTED_INVALID_SAMPLE))
    assert result.status == FINAL_STATUS_REJECTED


def test_rejected_final_label_is_none():
    result = resolve_final_label(_prediction(), _review(ReviewDecision.REJECTED_INVALID_SAMPLE))
    assert result.final_label is None


def test_rejected_human_review_completed_is_true():
    result = resolve_final_label(_prediction(), _review(ReviewDecision.REJECTED_INVALID_SAMPLE))
    assert result.human_review_completed is True


# ─────────────────────────────────────────────────────────────────────────────
# Prediction is never mutated
# ─────────────────────────────────────────────────────────────────────────────

def test_prediction_label_unchanged_after_confirmed():
    pred = _prediction(PredictedLabel.SUSPICIOUS_GROWTH)
    resolve_final_label(pred, _review(ReviewDecision.CONFIRMED))
    assert pred.predicted_label == PredictedLabel.SUSPICIOUS_GROWTH


def test_prediction_label_unchanged_after_corrected():
    pred = _prediction(PredictedLabel.SUSPICIOUS_GROWTH)
    resolve_final_label(
        pred,
        _review(ReviewDecision.CORRECTED, corrected_label=PredictedLabel.NO_EVIDENT_GROWTH),
    )
    assert pred.predicted_label == PredictedLabel.SUSPICIOUS_GROWTH


# ─────────────────────────────────────────────────────────────────────────────
# No taxonomy, no species/genus
# ─────────────────────────────────────────────────────────────────────────────

_FORBIDDEN = ("aspergillus", "penicillium", "botrytis", "escherichia", "salmonella",
              "diagnosis", "species", "genus")

def test_resolution_contains_no_taxonomy():
    for decision in ReviewDecision:
        corrected = (
            PredictedLabel.NO_EVIDENT_GROWTH if decision == ReviewDecision.CORRECTED else None
        )
        result = resolve_final_label(_prediction(), _review(decision, corrected_label=corrected))
        serialised = str(result).lower()
        for word in _FORBIDDEN:
            assert word not in serialised, f"Taxonomy '{word}' found in resolution for {decision}"
