from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.dataset_item import DatasetItem
from blueberry_microid.domain.entities.dataset_release import DatasetRelease
from blueberry_microid.domain.entities.dataset_snapshot import DatasetSnapshot
from blueberry_microid.domain.entities.dataset_split_item import DatasetSplitItem
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision


@dataclass(frozen=True, slots=True)
class CreateDatasetSnapshotRequest:
    name: str
    version: str
    description: Optional[str] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None
    include_inconclusive: bool = False
    include_rejected: bool = False


@dataclass(frozen=True, slots=True)
class DatasetSnapshotDTO:
    id: UUID
    name: str
    version: str
    description: Optional[str]
    created_at: datetime
    created_by: Optional[str]
    selection_criteria: Optional[dict]
    item_count: int
    label_distribution: Optional[dict[str, int]]
    notes: Optional[str]

    @classmethod
    def from_entity(cls, snapshot: DatasetSnapshot) -> "DatasetSnapshotDTO":
        return cls(
            id=snapshot.id,
            name=snapshot.name,
            version=snapshot.version,
            description=snapshot.description,
            created_at=snapshot.created_at,
            created_by=snapshot.created_by,
            selection_criteria=snapshot.selection_criteria,
            item_count=snapshot.item_count,
            label_distribution=snapshot.label_distribution,
            notes=snapshot.notes,
        )


@dataclass(frozen=True, slots=True)
class DatasetItemDTO:
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

    @classmethod
    def from_entity(cls, item: DatasetItem) -> "DatasetItemDTO":
        return cls(
            id=item.id,
            dataset_snapshot_id=item.dataset_snapshot_id,
            analysis_run_id=item.analysis_run_id,
            sample_id=item.sample_id,
            petri_image_id=item.petri_image_id,
            micro_image_id=item.micro_image_id,
            prediction_id=item.prediction_id,
            final_review_id=item.final_review_id,
            ground_truth_label=item.ground_truth_label,
            source_review_decision=item.source_review_decision,
            included=item.included,
            exclusion_reason=item.exclusion_reason,
            created_at=item.created_at,
        )


@dataclass(frozen=True, slots=True)
class CreateDatasetReleaseRequest:
    dataset_snapshot_id: UUID
    name: str
    version: str
    split_strategy: str = "random_by_sample"
    random_seed: int = 42
    train_ratio: float = 0.70
    validation_ratio: float = 0.15
    test_ratio: float = 0.15
    created_by: Optional[str] = None
    notes: Optional[str] = None


@dataclass(frozen=True, slots=True)
class DatasetReleaseDTO:
    id: UUID
    dataset_snapshot_id: UUID
    name: str
    version: str
    split_strategy: str
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

    @classmethod
    def from_entity(cls, release: DatasetRelease) -> "DatasetReleaseDTO":
        return cls(
            id=release.id,
            dataset_snapshot_id=release.dataset_snapshot_id,
            name=release.name,
            version=release.version,
            split_strategy=release.split_strategy,
            random_seed=release.random_seed,
            train_ratio=release.train_ratio,
            validation_ratio=release.validation_ratio,
            test_ratio=release.test_ratio,
            item_count=release.item_count,
            train_count=release.train_count,
            validation_count=release.validation_count,
            test_count=release.test_count,
            label_distribution=release.label_distribution,
            split_distribution=release.split_distribution,
            created_at=release.created_at,
            created_by=release.created_by,
            notes=release.notes,
        )


@dataclass(frozen=True, slots=True)
class DatasetSplitItemDTO:
    id: UUID
    dataset_release_id: UUID
    dataset_item_id: UUID
    sample_id: UUID
    split: DatasetSplit
    ground_truth_label: Optional[PredictedLabel]
    created_at: datetime

    @classmethod
    def from_entity(cls, item: DatasetSplitItem) -> "DatasetSplitItemDTO":
        return cls(
            id=item.id,
            dataset_release_id=item.dataset_release_id,
            dataset_item_id=item.dataset_item_id,
            sample_id=item.sample_id,
            split=item.split,
            ground_truth_label=item.ground_truth_label,
            created_at=item.created_at,
        )

