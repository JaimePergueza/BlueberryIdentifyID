from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.petri_region_review import PetriRegionReview
from blueberry_microid.domain.enums.petri_region_review_decision import PetriRegionReviewDecision


@dataclass(frozen=True, slots=True)
class SubmitPetriRegionReviewRequest:
    """Input for submitting a human review of one PetriSegmentationRegion."""

    petri_segmentation_region_id: UUID
    decision: PetriRegionReviewDecision
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


@dataclass(frozen=True, slots=True)
class PetriRegionReviewDTO:
    """Output representation of a PetriRegionReview, decoupled from the ORM."""

    id: UUID
    petri_segmentation_region_id: UUID
    petri_segmentation_run_id: UUID
    dataset_release_id: UUID
    dataset_item_id: UUID
    dataset_split_item_id: UUID
    decision: PetriRegionReviewDecision
    reviewer_id: Optional[str]
    reviewer_name: Optional[str]
    confidence_score: Optional[float]
    is_final: bool
    corrected_bbox_x: Optional[int]
    corrected_bbox_y: Optional[int]
    corrected_bbox_width: Optional[int]
    corrected_bbox_height: Optional[int]
    corrected_notes: Optional[str]
    review_notes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    @classmethod
    def from_entity(cls, review: PetriRegionReview) -> "PetriRegionReviewDTO":
        return cls(
            id=review.id,
            petri_segmentation_region_id=review.petri_segmentation_region_id,
            petri_segmentation_run_id=review.petri_segmentation_run_id,
            dataset_release_id=review.dataset_release_id,
            dataset_item_id=review.dataset_item_id,
            dataset_split_item_id=review.dataset_split_item_id,
            decision=review.decision,
            reviewer_id=review.reviewer_id,
            reviewer_name=review.reviewer_name,
            confidence_score=review.confidence_score,
            is_final=review.is_final,
            corrected_bbox_x=review.corrected_bbox_x,
            corrected_bbox_y=review.corrected_bbox_y,
            corrected_bbox_width=review.corrected_bbox_width,
            corrected_bbox_height=review.corrected_bbox_height,
            corrected_notes=review.corrected_notes,
            review_notes=review.review_notes,
            created_at=review.created_at,
            updated_at=review.updated_at,
        )
