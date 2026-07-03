from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from blueberry_microid.infrastructure.db.models.base import Base

if TYPE_CHECKING:
    from blueberry_microid.infrastructure.db.models.training_run import TrainingRunModel


class TrainingPredictionModel(Base):
    __tablename__ = "training_predictions"
    __table_args__ = (
        UniqueConstraint("training_run_id", "dataset_split_item_id", name="uq_training_predictions_run_split_item"),
        CheckConstraint("split IN ('train', 'validation', 'test')", name="ck_training_predictions_split"),
        CheckConstraint(
            "ground_truth_label IN ("
            "'no_evident_growth', 'suspicious_growth', 'probable_fungal_growth', "
            "'probable_bacterial_growth', 'inconclusive'"
            ")",
            name="ck_training_predictions_ground_truth_label",
        ),
        CheckConstraint(
            "predicted_label IN ("
            "'no_evident_growth', 'suspicious_growth', 'probable_fungal_growth', "
            "'probable_bacterial_growth', 'inconclusive'"
            ")",
            name="ck_training_predictions_predicted_label",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    training_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("training_runs.id"), nullable=False, index=True
    )
    dataset_split_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_split_items.id"), nullable=False, index=True
    )
    dataset_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_items.id"), nullable=False, index=True
    )
    split: Mapped[str] = mapped_column(String(32), nullable=False)
    ground_truth_label: Mapped[str] = mapped_column(String(64), nullable=False)
    predicted_label: Mapped[str] = mapped_column(String(64), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    training_run: Mapped["TrainingRunModel"] = relationship(back_populates="predictions")
