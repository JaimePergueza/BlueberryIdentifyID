from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from blueberry_microid.infrastructure.db.models.base import Base
from blueberry_microid.infrastructure.db.models.column_types import PortableJSON

if TYPE_CHECKING:
    from blueberry_microid.infrastructure.db.models.dataset_release import DatasetReleaseModel
    from blueberry_microid.infrastructure.db.models.petri_annotation_export_item import PetriAnnotationExportItemModel
    from blueberry_microid.infrastructure.db.models.petri_segmentation_run import PetriSegmentationRunModel


class PetriAnnotationExportRunModel(Base):
    __tablename__ = "petri_annotation_export_runs"
    __table_args__ = (
        CheckConstraint(
            "export_format IN ('blueberry_manifest', 'coco_json', 'yolo_txt')",
            name="ck_petri_annotation_export_runs_format",
        ),
        CheckConstraint("status IN ('completed', 'partial', 'failed')", name="ck_petri_annotation_export_runs_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_releases.id"), nullable=False, index=True
    )
    petri_segmentation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("petri_segmentation_runs.id"), nullable=False, index=True
    )
    export_format: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    config: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    exported_annotation_count: Mapped[int] = mapped_column(Integer, nullable=False)
    skipped_review_count: Mapped[int] = mapped_column(Integer, nullable=False)
    image_count: Mapped[int] = mapped_column(Integer, nullable=False)
    category_count: Mapped[int] = mapped_column(Integer, nullable=False)
    output_manifest: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    summary: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    dataset_release: Mapped["DatasetReleaseModel"] = relationship()
    petri_segmentation_run: Mapped["PetriSegmentationRunModel"] = relationship()
    items: Mapped[list["PetriAnnotationExportItemModel"]] = relationship(back_populates="export_run")
