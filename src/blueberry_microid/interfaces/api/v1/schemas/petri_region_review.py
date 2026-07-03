from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from blueberry_microid.domain.enums.petri_region_review_decision import PetriRegionReviewDecision


class PetriRegionReviewCreate(BaseModel):
    """Payload a reviewer submits to review a PetriSegmentationRegion candidate."""

    model_config = ConfigDict(extra="forbid")

    decision: PetriRegionReviewDecision
    reviewer_id: Optional[str] = None
    reviewer_name: Optional[str] = None
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    is_final: bool = True
    corrected_bbox_x: Optional[int] = None
    corrected_bbox_y: Optional[int] = None
    corrected_bbox_width: Optional[int] = Field(default=None, gt=0)
    corrected_bbox_height: Optional[int] = Field(default=None, gt=0)
    corrected_notes: Optional[str] = None
    review_notes: Optional[str] = None


class PetriRegionReviewRead(BaseModel):
    """Representation of a PetriRegionReview returned by the API."""

    model_config = ConfigDict(from_attributes=True)

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


class PetriRegionReviewListResponse(BaseModel):
    """Historical PetriRegionReview list, ordered oldest to newest."""

    reviews: list[PetriRegionReviewRead]


class PetriReviewedAnnotationResponse(BaseModel):
    petri_segmentation_region_id: UUID
    dataset_item_id: UUID
    dataset_split_item_id: UUID
    split: str
    petri_image_path: str
    original_bbox: dict[str, int]
    corrected_bbox: Optional[dict[str, int]]
    effective_bbox: dict[str, int]
    decision: str
    confidence_score: Optional[float]
    reviewer_id: Optional[str]
    is_final: bool
    created_at: Optional[str]


class PetriReviewedAnnotationManifestResponse(BaseModel):
    dataset_release_id: UUID
    petri_segmentation_run_id: UUID
    generated_at: Optional[str]
    total_regions: int
    reviewed_regions: int
    final_reviewed_regions: int
    decision_distribution: dict[str, int]
    annotations: list[PetriReviewedAnnotationResponse]

    model_config = ConfigDict(extra="allow")
