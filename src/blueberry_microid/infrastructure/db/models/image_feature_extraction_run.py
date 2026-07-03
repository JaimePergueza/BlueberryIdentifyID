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
    from blueberry_microid.infrastructure.db.models.image_dataset_audit_run import ImageDatasetAuditRunModel
    from blueberry_microid.infrastructure.db.models.image_feature_vector import ImageFeatureVectorModel


class ImageFeatureExtractionRunModel(Base):
    """Persisted non-deep feature extraction run over an audited
    DatasetRelease's Petri/micro images."""

    __tablename__ = "image_feature_extraction_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('completed', 'failed', 'partial')", name="ck_image_feature_extraction_runs_status"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_releases.id"), nullable=False, index=True
    )
    image_audit_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("image_dataset_audit_runs.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    config: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    total_items: Mapped[int] = mapped_column(Integer, nullable=False)
    processed_items: Mapped[int] = mapped_column(Integer, nullable=False)
    failed_items: Mapped[int] = mapped_column(Integer, nullable=False)
    total_feature_vectors: Mapped[int] = mapped_column(Integer, nullable=False)
    petri_feature_count: Mapped[int] = mapped_column(Integer, nullable=False)
    micro_feature_count: Mapped[int] = mapped_column(Integer, nullable=False)
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
    image_audit_run: Mapped["ImageDatasetAuditRunModel"] = relationship()
    vectors: Mapped[list["ImageFeatureVectorModel"]] = relationship(back_populates="feature_extraction_run")
