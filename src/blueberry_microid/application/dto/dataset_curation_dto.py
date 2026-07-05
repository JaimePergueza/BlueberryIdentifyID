from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.dataset_curation_item import DatasetCurationItem
from blueberry_microid.domain.entities.dataset_curation_run import DatasetCurationRun
from blueberry_microid.domain.enums.dataset_curation_run_status import DatasetCurationRunStatus
from blueberry_microid.domain.enums.dataset_curation_status import DatasetCurationStatus
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision


@dataclass(frozen=True, slots=True)
class DatasetCurationPolicy:
    include_confirmed: bool = True
    include_corrected: bool = True
    include_marked_inconclusive: bool = True
    require_final_human_review: bool = True
    require_petri_image: bool = True
    require_micro_image: bool = True
    require_prediction: bool = True
    prevent_duplicates: bool = True
    allowed_labels: tuple[PredictedLabel, ...] = (
        PredictedLabel.NO_EVIDENT_GROWTH,
        PredictedLabel.SUSPICIOUS_GROWTH,
        PredictedLabel.PROBABLE_FUNGAL_GROWTH,
        PredictedLabel.PROBABLE_BACTERIAL_GROWTH,
        PredictedLabel.INCONCLUSIVE,
    )

    def to_dict(self) -> dict:
        return {
            "include_confirmed": self.include_confirmed,
            "include_corrected": self.include_corrected,
            "include_marked_inconclusive": self.include_marked_inconclusive,
            "require_final_human_review": self.require_final_human_review,
            "require_petri_image": self.require_petri_image,
            "require_micro_image": self.require_micro_image,
            "require_prediction": self.require_prediction,
            "prevent_duplicates": self.prevent_duplicates,
            "allowed_labels": [label.value for label in self.allowed_labels],
        }


@dataclass(frozen=True, slots=True)
class CreateDatasetCurationRunRequest:
    analysis_run_ids: Optional[list[UUID]] = None
    policy: DatasetCurationPolicy = field(default_factory=DatasetCurationPolicy)
    explicit_all_reviewed: bool = False
    create_snapshot: bool = False
    snapshot_name: Optional[str] = None
    snapshot_version: Optional[str] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None


@dataclass(frozen=True, slots=True)
class CuratedAnalysisCandidateDTO:
    analysis_run_id: UUID
    sample_id: UUID
    petri_image_id: Optional[UUID]
    micro_image_id: Optional[UUID]
    prediction_id: Optional[UUID]
    human_review_id: Optional[UUID]
    automatic_label: Optional[PredictedLabel]
    final_label: Optional[PredictedLabel]
    review_decision: Optional[ReviewDecision]
    curation_status: DatasetCurationStatus
    exclusion_reason: Optional[str]
    provenance: dict
    feature_summary: Optional[dict]
    quality_summary: Optional[dict]


@dataclass(frozen=True, slots=True)
class DatasetCurationItemDTO:
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
    provenance: Optional[dict]
    feature_summary: Optional[dict]
    quality_summary: Optional[dict]
    created_at: datetime

    @classmethod
    def from_entity(cls, item: DatasetCurationItem) -> "DatasetCurationItemDTO":
        return cls(
            id=item.id,
            curation_run_id=item.curation_run_id,
            sample_id=item.sample_id,
            analysis_run_id=item.analysis_run_id,
            prediction_id=item.prediction_id,
            human_review_id=item.human_review_id,
            petri_image_id=item.petri_image_id,
            micro_image_id=item.micro_image_id,
            automatic_label=item.automatic_label,
            final_label=item.final_label,
            review_decision=item.review_decision,
            curation_status=item.curation_status,
            exclusion_reason=item.exclusion_reason,
            provenance=item.provenance,
            feature_summary=item.feature_summary,
            quality_summary=item.quality_summary,
            created_at=item.created_at,
        )


@dataclass(frozen=True, slots=True)
class DatasetCurationRunDTO:
    id: UUID
    status: DatasetCurationRunStatus
    policy: Optional[dict]
    total_candidates_scanned: int
    included_count: int
    excluded_count: int
    created_snapshot_id: Optional[UUID]
    issues: Optional[list[dict]]
    created_by: Optional[str]
    notes: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    @classmethod
    def from_entity(cls, run: DatasetCurationRun) -> "DatasetCurationRunDTO":
        return cls(
            id=run.id,
            status=run.status,
            policy=run.policy,
            total_candidates_scanned=run.total_candidates_scanned,
            included_count=run.included_count,
            excluded_count=run.excluded_count,
            created_snapshot_id=run.created_snapshot_id,
            issues=run.issues,
            created_by=run.created_by,
            notes=run.notes,
            created_at=run.created_at,
            completed_at=run.completed_at,
        )


@dataclass(frozen=True, slots=True)
class SnapshotFromCurationPolicy:
    include_only_status: tuple[DatasetCurationStatus, ...] = (DatasetCurationStatus.INCLUDED,)
    require_completed_curation_run: bool = True
    require_human_review_id: bool = True
    require_prediction_id: bool = True
    require_petri_image_id: bool = True
    require_micro_image_id: bool = True
    require_final_label: bool = True
    prevent_duplicate_analysis_runs: bool = True
    prevent_duplicate_samples: bool = False
    include_inconclusive: bool = True
    allow_empty_snapshot: bool = False
    allowed_labels: tuple[PredictedLabel, ...] = tuple(PredictedLabel)


@dataclass(frozen=True, slots=True)
class SnapshotFromCurationRunRequestDTO:
    curation_run_id: UUID
    snapshot_name: Optional[str] = None
    snapshot_description: Optional[str] = None
    created_by: Optional[str] = None
    include_inconclusive: bool = True
    allow_empty_snapshot: bool = False
    notes: Optional[str] = None


@dataclass(frozen=True, slots=True)
class SnapshotCurationItemMappingDTO:
    dataset_item_id: UUID
    curation_item_id: UUID
    sample_id: UUID
    analysis_run_id: UUID
    prediction_id: UUID
    human_review_id: UUID
    final_label: PredictedLabel
    review_decision: ReviewDecision
    status: str


@dataclass(frozen=True, slots=True)
class SnapshotFromCurationRunResultDTO:
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
    provenance: dict
    mappings: list[SnapshotCurationItemMappingDTO]
