from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from blueberry_microid.infrastructure.db.models.base import Base
from blueberry_microid.infrastructure.db.models.column_types import PortableJSON

if TYPE_CHECKING:
    from blueberry_microid.infrastructure.db.models.dataset_release import DatasetReleaseModel
    from blueberry_microid.infrastructure.db.models.image_dataset_audit_run import ImageDatasetAuditRunModel
    from blueberry_microid.infrastructure.db.models.petri_segmentation_region import PetriSegmentationRegionModel


class PetriSegmentationRunModel(Base):
    __tablename__ = "petri_segmentation_runs"
    __table_args__ = (
        CheckConstraint("status IN ('completed', 'partial', 'failed')", name="ck_petri_segmentation_runs_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_releases.id"), nullable=False, index=True
    )
    image_audit_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("image_dataset_audit_runs.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    config: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    total_items: Mapped[int] = mapped_column(Integer, nullable=False)
    processed_petri_images: Mapped[int] = mapped_column(Integer, nullable=False)
    failed_petri_images: Mapped[int] = mapped_column(Integer, nullable=False)
    total_regions_detected: Mapped[int] = mapped_column(Integer, nullable=False)
    mean_regions_per_image: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    summary: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    dataset_release: Mapped["DatasetReleaseModel"] = relationship()
    image_audit_run: Mapped[Optional["ImageDatasetAuditRunModel"]] = relationship()
    regions: Mapped[list["PetriSegmentationRegionModel"]] = relationship(back_populates="segmentation_run")
