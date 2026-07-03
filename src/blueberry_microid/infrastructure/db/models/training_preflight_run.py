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
    from blueberry_microid.infrastructure.db.models.training_preflight_issue import TrainingPreflightIssueModel


class TrainingPreflightRunModel(Base):
    """Persisted validation report for future-training readiness."""

    __tablename__ = "training_preflight_runs"
    __table_args__ = (
        CheckConstraint("status IN ('passed', 'failed', 'warning')", name="ck_training_preflight_runs_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_releases.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    config: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    summary: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False)
    train_count: Mapped[int] = mapped_column(Integer, nullable=False)
    validation_count: Mapped[int] = mapped_column(Integer, nullable=False)
    test_count: Mapped[int] = mapped_column(Integer, nullable=False)
    label_counts: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    split_counts: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    split_label_counts: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    leakage_checks: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    recommendation_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    dataset_release: Mapped["DatasetReleaseModel"] = relationship()
    issues: Mapped[list["TrainingPreflightIssueModel"]] = relationship(back_populates="preflight_run")
