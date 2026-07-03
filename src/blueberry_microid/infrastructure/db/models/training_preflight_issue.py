from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from blueberry_microid.infrastructure.db.models.base import Base

if TYPE_CHECKING:
    from blueberry_microid.infrastructure.db.models.training_preflight_run import TrainingPreflightRunModel


class TrainingPreflightIssueModel(Base):
    """Persisted error/warning emitted by preflight validation."""

    __tablename__ = "training_preflight_issues"
    __table_args__ = (
        CheckConstraint("severity IN ('error', 'warning')", name="ck_training_preflight_issues_severity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    preflight_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("training_preflight_runs.id"), nullable=False, index=True
    )
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    field: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    item_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    preflight_run: Mapped["TrainingPreflightRunModel"] = relationship(back_populates="issues")
