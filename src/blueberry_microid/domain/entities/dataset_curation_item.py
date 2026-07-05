from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.dataset_curation_status import DatasetCurationStatus
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class DatasetCurationItem:
    """One audited curation decision for an AnalysisRun."""

    curation_run_id: UUID
    curation_status: DatasetCurationStatus
    id: UUID = field(default_factory=uuid4)
    sample_id: Optional[UUID] = None
    analysis_run_id: Optional[UUID] = None
    prediction_id: Optional[UUID] = None
    human_review_id: Optional[UUID] = None
    petri_image_id: Optional[UUID] = None
    micro_image_id: Optional[UUID] = None
    automatic_label: Optional[PredictedLabel] = None
    final_label: Optional[PredictedLabel] = None
    review_decision: Optional[ReviewDecision] = None
    exclusion_reason: Optional[str] = None
    provenance: Optional[dict] = None
    feature_summary: Optional[dict] = None
    quality_summary: Optional[dict] = None
    created_at: datetime = field(default_factory=_utcnow)

