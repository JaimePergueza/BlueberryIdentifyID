from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision


class DatasetSnapshotCreate(BaseModel):
    name: str
    version: str
    description: Optional[str] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None
    include_inconclusive: bool = False
    include_rejected: bool = False


class DatasetSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    version: str
    description: Optional[str]
    created_at: datetime
    created_by: Optional[str]
    selection_criteria: Optional[dict[str, Any]]
    item_count: int
    label_distribution: Optional[dict[str, int]]
    notes: Optional[str]


class DatasetItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_snapshot_id: UUID
    analysis_run_id: UUID
    sample_id: UUID
    petri_image_id: UUID
    micro_image_id: UUID
    prediction_id: UUID
    final_review_id: UUID
    ground_truth_label: Optional[PredictedLabel]
    source_review_decision: ReviewDecision
    included: bool
    exclusion_reason: Optional[str]
    created_at: datetime

