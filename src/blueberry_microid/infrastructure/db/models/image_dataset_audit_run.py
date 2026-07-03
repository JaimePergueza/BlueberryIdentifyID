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
    from blueberry_microid.infrastructure.db.models.image_dataset_audit_issue import ImageDatasetAuditIssueModel


class ImageDatasetAuditRunModel(Base):
    """Persisted technical audit of the image files referenced by a
    DatasetRelease — file existence/readability/format/dimensions/color
    mode, never model performance metrics or taxonomy."""

    __tablename__ = "image_dataset_audit_runs"
    __table_args__ = (
        CheckConstraint("status IN ('passed', 'failed', 'warning')", name="ck_image_dataset_audit_runs_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_releases.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    is_passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    total_items: Mapped[int] = mapped_column(Integer, nullable=False)
    total_petri_images: Mapped[int] = mapped_column(Integer, nullable=False)
    total_micro_images: Mapped[int] = mapped_column(Integer, nullable=False)
    checked_petri_images: Mapped[int] = mapped_column(Integer, nullable=False)
    checked_micro_images: Mapped[int] = mapped_column(Integer, nullable=False)
    failed_petri_images: Mapped[int] = mapped_column(Integer, nullable=False)
    failed_micro_images: Mapped[int] = mapped_column(Integer, nullable=False)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    format_distribution: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    color_mode_distribution: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    dimension_distribution: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    file_size_distribution: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    dataset_release: Mapped["DatasetReleaseModel"] = relationship()
    issues: Mapped[list["ImageDatasetAuditIssueModel"]] = relationship(back_populates="audit_run")
