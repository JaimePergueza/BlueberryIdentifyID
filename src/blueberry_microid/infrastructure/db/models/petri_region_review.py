from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from blueberry_microid.infrastructure.db.models.base import Base

if TYPE_CHECKING:
    from blueberry_microid.infrastructure.db.models.petri_segmentation_region import PetriSegmentationRegionModel


class PetriRegionReviewModel(Base):
    """A human review of a PetriSegmentationRegion candidate.

    Never overwrites the original PetriSegmentationRegionModel row. Multiple
    reviews per region are allowed over time, to preserve full audit
    history — but a partial unique index guarantees at most one of them has
    `is_final=True` at any given time.
    """

    __tablename__ = "petri_region_reviews"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('candidate_valid', 'candidate_false_positive', 'candidate_uncertain', "
            "'needs_resegmentation')",
            name="ck_petri_region_reviews_decision",
        ),
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_petri_region_reviews_confidence_score",
        ),
        CheckConstraint(
            "corrected_bbox_width IS NULL OR corrected_bbox_width > 0",
            name="ck_petri_region_reviews_corrected_bbox_width",
        ),
        CheckConstraint(
            "corrected_bbox_height IS NULL OR corrected_bbox_height > 0",
            name="ck_petri_region_reviews_corrected_bbox_height",
        ),
        Index(
            "uq_petri_region_reviews_one_final_per_region",
            "petri_segmentation_region_id",
            unique=True,
            postgresql_where=text("is_final = true"),
            sqlite_where=text("is_final = 1"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    petri_segmentation_region_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("petri_segmentation_regions.id"), nullable=False, index=True
    )
    petri_segmentation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("petri_segmentation_runs.id"), nullable=False, index=True
    )
    dataset_release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_releases.id"), nullable=False, index=True
    )
    dataset_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_items.id"), nullable=False, index=True
    )
    dataset_split_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_split_items.id"), nullable=False, index=True
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    reviewer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reviewer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    is_final: Mapped[bool] = mapped_column(nullable=False, server_default="true")
    corrected_bbox_x: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    corrected_bbox_y: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    corrected_bbox_width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    corrected_bbox_height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    corrected_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    region: Mapped["PetriSegmentationRegionModel"] = relationship()
