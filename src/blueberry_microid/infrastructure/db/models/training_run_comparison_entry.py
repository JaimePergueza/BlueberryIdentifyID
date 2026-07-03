from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from blueberry_microid.infrastructure.db.models.base import Base
from blueberry_microid.infrastructure.db.models.column_types import PortableJSON

if TYPE_CHECKING:
    from blueberry_microid.infrastructure.db.models.training_run_comparison import TrainingRunComparisonModel


class TrainingRunComparisonEntryModel(Base):
    __tablename__ = "training_run_comparison_entries"
    __table_args__ = (
        UniqueConstraint("comparison_id", "training_run_id", name="uq_training_run_comparison_entries_run"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comparison_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("training_run_comparisons.id"), nullable=False, index=True
    )
    training_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("training_runs.id"), nullable=False, index=True
    )
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    run_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    baseline_model_type: Mapped[str] = mapped_column(String(64), nullable=False)
    primary_metric_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    train_accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    validation_accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    test_accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    generalization_gap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    support_train: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    support_validation: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    support_test: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    metrics_snapshot: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    summary: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    comparison: Mapped["TrainingRunComparisonModel"] = relationship(back_populates="entries")
