from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.petri_region_review_decision import PetriRegionReviewDecision
from blueberry_microid.domain.value_objects.confidence_score import ConfidenceScore


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PetriRegionReview:
    """A human review of a PetriSegmentationRegion candidate.

    Never overwrites the original PetriSegmentationRegion — a corrected
    bounding box, if any, is stored only on this review row. `is_final`
    distinguishes the review that currently stands for a region from
    historical ones; at most one PetriRegionReview per region should have
    `is_final=True` at any given time. This entity cannot enforce that by
    itself since the invariant spans multiple rows — it is enforced at the
    database level with a partial unique index and by
    SubmitPetriRegionReviewUseCase, which demotes any previous final review
    before adding the new final review in one UnitOfWork.

    A `candidate_valid` decision means only that the region looks like a
    useful annotation candidate — never a confirmed colony, a taxon, or a
    microbiological diagnosis.
    """

    petri_segmentation_region_id: UUID
    petri_segmentation_run_id: UUID
    dataset_release_id: UUID
    dataset_item_id: UUID
    dataset_split_item_id: UUID
    decision: PetriRegionReviewDecision
    id: UUID = field(default_factory=uuid4)
    reviewer_id: Optional[str] = None
    reviewer_name: Optional[str] = None
    confidence_score: Optional[float] = None
    is_final: bool = True
    corrected_bbox_x: Optional[int] = None
    corrected_bbox_y: Optional[int] = None
    corrected_bbox_width: Optional[int] = None
    corrected_bbox_height: Optional[int] = None
    corrected_notes: Optional[str] = None
    review_notes: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.confidence_score is not None:
            self.confidence_score = float(ConfidenceScore(self.confidence_score))
        if self.corrected_bbox_width is not None and self.corrected_bbox_width <= 0:
            raise ValueError("corrected_bbox_width must be positive when provided")
        if self.corrected_bbox_height is not None and self.corrected_bbox_height <= 0:
            raise ValueError("corrected_bbox_height must be positive when provided")
