from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class DatasetItem:
    """One AnalysisRun reference captured inside a DatasetSnapshot."""

    dataset_snapshot_id: UUID
    analysis_run_id: UUID
    sample_id: UUID
    petri_image_id: UUID
    micro_image_id: UUID
    prediction_id: UUID
    final_review_id: UUID
    source_review_decision: ReviewDecision
    id: UUID = field(default_factory=uuid4)
    curation_run_id: Optional[UUID] = None
    curation_item_id: Optional[UUID] = None
    ground_truth_label: Optional[PredictedLabel] = None
    included: bool = True
    exclusion_reason: Optional[str] = None
    provenance: Optional[dict] = None
    created_at: datetime = field(default_factory=_utcnow)

