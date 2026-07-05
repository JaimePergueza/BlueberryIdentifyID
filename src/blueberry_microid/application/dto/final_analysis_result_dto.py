"""DTO for the final analysis result endpoint (Fase 42).

Combines the automatic Prediction with the current HumanReview (if any) and
exposes a resolved ``final_label`` and ``status``.  Internal file paths are
never included.  No taxonomic claims, species, genus, or diagnosis.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision

_FINAL_RESULT_DISCLAIMER = (
    "PRELIMINARY RESULT — expert review required. "
    "This system provides preliminary visual categories only. "
    "It does not identify species, genus, or provide any microbiological diagnosis. "
    "The automatic result is produced by a classical image-processing heuristic (no deep learning). "
    "The final label, if present, reflects the expert reviewer's assessment. "
    "Neither the automatic result nor the human-reviewed result constitutes a clinical or "
    "scientific microbiological identification."
)


@dataclass(frozen=True, slots=True)
class FinalAnalysisResultDTO:
    """Full final-result view combining automatic Prediction and HumanReview."""

    # ── Identifiers ───────────────────────────────────────────────────────────
    analysis_run_id: UUID
    sample_id: UUID
    prediction_id: UUID

    # ── Automatic result (Prediction, never modified) ─────────────────────────
    preliminary_label: PredictedLabel
    confidence_score: Optional[float]
    explanation: Optional[str]
    feature_summary: Optional[dict]
    quality_summary: Optional[dict]
    decision_trace: Optional[list]
    automatic_warnings: Optional[list]

    # ── Human review (None when not yet reviewed) ─────────────────────────────
    human_review_id: Optional[UUID]
    human_review_decision: Optional[ReviewDecision]
    corrected_label: Optional[PredictedLabel]
    reviewer_name: Optional[str]
    human_comments: Optional[str]
    reviewed_at: Optional[datetime]

    # ── Resolution ────────────────────────────────────────────────────────────
    final_label: Optional[PredictedLabel]
    status: str  # one of FINAL_STATUS_* from final_analysis_resolver
    human_review_completed: bool
    requires_human_review: bool

    # ── Always present ────────────────────────────────────────────────────────
    disclaimer: str
