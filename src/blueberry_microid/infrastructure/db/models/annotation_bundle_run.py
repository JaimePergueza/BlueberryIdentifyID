from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from blueberry_microid.infrastructure.db.models.base import Base
from blueberry_microid.infrastructure.db.models.column_types import PortableJSON


class AnnotationBundleRunModel(Base):
    __tablename__ = "annotation_bundle_runs"
    __table_args__ = (
        CheckConstraint("status IN ('completed', 'failed', 'dry_run')", name="ck_annotation_bundle_runs_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    petri_annotation_export_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("petri_annotation_export_runs.id"), nullable=False, index=True
    )
    dataset_release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_releases.id"), nullable=False, index=True
    )
    petri_segmentation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("petri_segmentation_runs.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    config: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    output_dir: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False)
    annotation_count: Mapped[int] = mapped_column(Integer, nullable=False)
    image_count: Mapped[int] = mapped_column(Integer, nullable=False)
    label_count: Mapped[int] = mapped_column(Integer, nullable=False)
    validation_summary: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    bundle_manifest: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
