from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from blueberry_microid.infrastructure.db.models.base import Base
from blueberry_microid.infrastructure.db.models.column_types import PortableJSON

if TYPE_CHECKING:
    from blueberry_microid.infrastructure.db.models.image_dataset_audit_run import ImageDatasetAuditRunModel


class ImageDatasetAuditIssueModel(Base):
    """Persisted error/warning emitted by an ImageDatasetAuditRun for one
    Petri or micro image file."""

    __tablename__ = "image_dataset_audit_issues"
    __table_args__ = (
        CheckConstraint("severity IN ('error', 'warning')", name="ck_image_dataset_audit_issues_severity"),
        CheckConstraint("modality IN ('petri', 'micro')", name="ck_image_dataset_audit_issues_modality"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("image_dataset_audit_runs.id"), nullable=False, index=True
    )
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    modality: Mapped[str] = mapped_column(String(16), nullable=False)
    dataset_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_items.id"), nullable=True
    )
    dataset_split_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_split_items.id"), nullable=True
    )
    image_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    audit_run: Mapped["ImageDatasetAuditRunModel"] = relationship(back_populates="issues")
