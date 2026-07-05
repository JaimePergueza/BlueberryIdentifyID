from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.dataset_curation_run_status import DatasetCurationRunStatus
from blueberry_microid.domain.enums.dataset_curation_status import DatasetCurationStatus
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision
from blueberry_microid.domain.enums.split_strategy import SplitStrategy


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
    curation_run_id: Optional[UUID] = None
    curation_item_id: Optional[UUID] = None
    ground_truth_label: Optional[PredictedLabel]
    source_review_decision: ReviewDecision
    included: bool
    exclusion_reason: Optional[str]
    provenance: Optional[dict[str, Any]] = None
    created_at: datetime


class DatasetSnapshotFromCurationRunCreate(BaseModel):
    curation_run_id: UUID
    snapshot_name: Optional[str] = None
    snapshot_description: Optional[str] = None
    include_inconclusive: bool = True
    allow_empty_snapshot: bool = False
    created_by: Optional[str] = None
    notes: Optional[str] = None


class DatasetSnapshotFromCurationRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    snapshot_id: UUID
    curation_run_id: UUID
    status: str
    snapshot_name: str
    total_curation_items: int
    included_items_scanned: int
    dataset_items_created: int
    excluded_items_ignored: int
    duplicate_items_skipped: int
    labels_distribution: dict[str, int]
    created_by: Optional[str]
    created_at: datetime
    warnings: list[str]
    provenance: dict[str, Any]


class DatasetReleaseCreate(BaseModel):
    dataset_snapshot_id: UUID
    name: str
    version: str
    split_strategy: SplitStrategy = SplitStrategy.BY_SAMPLE
    random_seed: int = 42
    train_ratio: float = 0.70
    validation_ratio: float = 0.15
    test_ratio: float = 0.15
    created_by: Optional[str] = None
    notes: Optional[str] = None


class DatasetReleaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_snapshot_id: UUID
    name: str
    version: str
    split_strategy: SplitStrategy
    random_seed: int
    train_ratio: float
    validation_ratio: float
    test_ratio: float
    item_count: int
    train_count: int
    validation_count: int
    test_count: int
    label_distribution: Optional[dict[str, int]]
    split_distribution: Optional[dict[str, dict[str, int]]]
    created_at: datetime
    created_by: Optional[str]
    notes: Optional[str]


class DatasetSplitItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_release_id: UUID
    dataset_item_id: UUID
    sample_id: UUID
    split: DatasetSplit
    ground_truth_label: Optional[PredictedLabel]
    created_at: datetime


class DatasetCurationPolicySchema(BaseModel):
    include_confirmed: bool = True
    include_corrected: bool = True
    include_marked_inconclusive: bool = True
    require_final_human_review: bool = True
    require_petri_image: bool = True
    require_micro_image: bool = True
    require_prediction: bool = True
    prevent_duplicates: bool = True
    allowed_labels: Optional[list[PredictedLabel]] = None


class DatasetCurationRunCreate(BaseModel):
    analysis_run_ids: Optional[list[UUID]] = None
    policy: DatasetCurationPolicySchema = DatasetCurationPolicySchema()
    explicit_all_reviewed: bool = False
    create_snapshot: bool = False
    snapshot_name: Optional[str] = None
    snapshot_version: Optional[str] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None


class DatasetCurationRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: DatasetCurationRunStatus
    policy: Optional[dict[str, Any]]
    total_candidates_scanned: int
    included_count: int
    excluded_count: int
    created_snapshot_id: Optional[UUID]
    issues: Optional[list[dict[str, Any]]]
    created_by: Optional[str]
    notes: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]


class DatasetCurationItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    curation_run_id: UUID
    sample_id: Optional[UUID]
    analysis_run_id: Optional[UUID]
    prediction_id: Optional[UUID]
    human_review_id: Optional[UUID]
    petri_image_id: Optional[UUID]
    micro_image_id: Optional[UUID]
    automatic_label: Optional[PredictedLabel]
    final_label: Optional[PredictedLabel]
    review_decision: Optional[ReviewDecision]
    curation_status: DatasetCurationStatus
    exclusion_reason: Optional[str]
    provenance: Optional[dict[str, Any]]
    feature_summary: Optional[dict[str, Any]]
    quality_summary: Optional[dict[str, Any]]
    created_at: datetime

