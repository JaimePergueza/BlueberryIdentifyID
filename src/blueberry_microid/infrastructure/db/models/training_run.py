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
    from blueberry_microid.infrastructure.db.models.training_prediction import TrainingPredictionModel


class TrainingRunModel(Base):
    __tablename__ = "training_runs"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'running', 'completed', 'failed')", name="ck_training_runs_status"),
        CheckConstraint("run_kind IN ('baseline')", name="ck_training_runs_run_kind"),
        CheckConstraint("baseline_model_type IN ('majority_class')", name="ck_training_runs_baseline_model_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_releases.id"), nullable=False, index=True
    )
    preflight_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("training_preflight_runs.id"), nullable=False, index=True
    )
    run_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    baseline_model_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    experiment_name: Mapped[str] = mapped_column(String(255), nullable=False)
    config: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    baseline_state: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    metrics: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    summary: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    predictions: Mapped[list["TrainingPredictionModel"]] = relationship(back_populates="training_run")
