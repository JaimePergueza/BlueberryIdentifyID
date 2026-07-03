from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from blueberry_microid.infrastructure.db.models.base import Base
from blueberry_microid.infrastructure.db.models.column_types import PortableJSON

if TYPE_CHECKING:
    from blueberry_microid.infrastructure.db.models.petri_segmentation_run import PetriSegmentationRunModel


class PetriSegmentationRegionModel(Base):
    __tablename__ = "petri_segmentation_regions"
    __table_args__ = (
        UniqueConstraint(
            "segmentation_run_id",
            "dataset_split_item_id",
            "region_index",
            name="uq_petri_segmentation_regions_run_split_item_index",
        ),
        CheckConstraint("split IN ('train', 'validation', 'test')", name="ck_petri_segmentation_regions_split"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    segmentation_run_id: Mapped[uuid.UUID] = mapped_column(
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
    split: Mapped[str] = mapped_column(String(32), nullable=False)
    petri_image_path: Mapped[str] = mapped_column(Text, nullable=False)
    region_index: Mapped[int] = mapped_column(Integer, nullable=False)
    area_px: Mapped[float] = mapped_column(Float, nullable=False)
    perimeter_px: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    centroid_x: Mapped[float] = mapped_column(Float, nullable=False)
    centroid_y: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_x: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_y: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_width: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_height: Mapped[int] = mapped_column(Integer, nullable=False)
    circularity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    solidity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    mean_intensity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    region_features: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    segmentation_run: Mapped["PetriSegmentationRunModel"] = relationship(back_populates="regions")
