"""Pydantic schemas for the final-result endpoint (Fase 42)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision


class FinalAnalysisResultRead(BaseModel):
    """Response for GET /api/v1/analysis-runs/{id}/final-result.

    Combines the automatic Prediction (never modified) with the expert
    HumanReview (if submitted).  ``final_label`` and ``status`` reflect the
    expert decision; they are ``null``/``pending_human_review`` until a review
    is submitted.

    No internal file paths, no taxonomy, no species/genus, no diagnosis.
    """

    model_config = {"from_attributes": True}

    # ── Identifiers ───────────────────────────────────────────────────────────
    analysis_run_id: UUID
    sample_id: UUID
    prediction_id: UUID

    # ── Automatic result (original Prediction, immutable) ─────────────────────
    preliminary_label: PredictedLabel = Field(
        description="Preliminary visual category produced by the automatic engine (non-diagnostic)."
    )
    confidence_score: Optional[float] = Field(
        default=None,
        description="Heuristic confidence score in [0, 1] from the automatic engine.",
    )
    explanation: Optional[str] = Field(
        default=None,
        description="Human-readable description of the heuristic signals (automatic).",
    )
    feature_summary: Optional[dict[str, Any]] = Field(
        default=None,
        description="Extracted visual feature values from both images (automatic).",
    )
    quality_summary: Optional[dict[str, Any]] = Field(
        default=None,
        description="Image quality flags from the automatic engine.",
    )
    decision_trace: Optional[list[Any]] = Field(
        default=None,
        description="Step-by-step heuristic rule trace (automatic).",
    )
    automatic_warnings: Optional[list[str]] = Field(
        default=None,
        description="Non-blocking warnings from the automatic engine.",
    )

    # ── Human review ─────────────────────────────────────────────────────────
    human_review_id: Optional[UUID] = Field(
        default=None,
        description="ID of the current final HumanReview, if one has been submitted.",
    )
    human_review_decision: Optional[ReviewDecision] = Field(
        default=None,
        description="Expert decision (confirmed / corrected / marked_inconclusive / rejected_invalid_sample).",
    )
    corrected_label: Optional[PredictedLabel] = Field(
        default=None,
        description="Label chosen by the expert when decision is 'corrected'.",
    )
    reviewer_name: Optional[str] = Field(
        default=None,
        description="Name of the expert reviewer.",
    )
    human_comments: Optional[str] = Field(
        default=None,
        description="Free-text technical observation from the expert.",
    )
    reviewed_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp of the human review.",
    )

    # ── Resolved final state ──────────────────────────────────────────────────
    final_label: Optional[PredictedLabel] = Field(
        default=None,
        description=(
            "Resolved final visual category. "
            "null when no human review exists or when the sample was rejected. "
            "This is NOT a microbiological identification."
        ),
    )
    status: str = Field(
        description=(
            "Workflow status: pending_human_review | human_confirmed | "
            "human_corrected | inconclusive | rejected_invalid_sample."
        )
    )
    human_review_completed: bool = Field(
        description="True if any final human review has been submitted."
    )
    requires_human_review: bool = Field(
        description="True while no final human review has been submitted."
    )

    # ── Always present ────────────────────────────────────────────────────────
    disclaimer: str = Field(
        description="Mandatory disclaimer: results carry no diagnostic or taxonomic validity."
    )
