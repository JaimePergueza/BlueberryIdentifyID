from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from blueberry_microid.infrastructure.db.models.base import Base
from blueberry_microid.infrastructure.db.models.column_types import PortableJSON

if TYPE_CHECKING:
    from blueberry_microid.infrastructure.db.models.petri_annotation_export_run import PetriAnnotationExportRunModel


class PetriAnnotationExportItemModel(Base):
    __tablename__ = "petri_annotation_export_items"
    __table_args__ = (
        CheckConstraint("bbox_width > 0", name="ck_petri_annotation_export_items_bbox_width"),
        CheckConstraint("bbox_height > 0", name="ck_petri_annotation_export_items_bbox_height"),
        CheckConstraint("bbox_source IN ('corrected', 'original')", name="ck_petri_annotation_export_items_bbox_source"),
        UniqueConstraint("export_run_id", "petri_region_review_id", name="uq_petri_annotation_export_items_run_review"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    export_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("petri_annotation_export_runs.id"), nullable=False, index=True
    )
    petri_region_review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("petri_region_reviews.id"), nullable=False, index=True
    )
    petri_segmentation_region_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("petri_segmentation_regions.id"), nullable=False, index=True
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
    split: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    petri_image_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    export_label: Mapped[str] = mapped_column(String(64), nullable=False)
    bbox_x: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_y: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_width: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_height: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_source: Mapped[str] = mapped_column(String(16), nullable=False)
    export_payload: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    export_run: Mapped["PetriAnnotationExportRunModel"] = relationship(back_populates="items")
