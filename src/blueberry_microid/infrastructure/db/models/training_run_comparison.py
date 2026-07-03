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
    from blueberry_microid.infrastructure.db.models.training_run_comparison_entry import (
        TrainingRunComparisonEntryModel,
    )


class TrainingRunComparisonModel(Base):
    __tablename__ = "training_run_comparisons"
    __table_args__ = (
        CheckConstraint("primary_metric IN ('accuracy')", name="ck_training_run_comparisons_primary_metric"),
        CheckConstraint("primary_split IN ('validation', 'test')", name="ck_training_run_comparisons_primary_split"),
        CheckConstraint(
            "selection_policy IN ('best_primary_metric', 'prefer_simpler_if_tie', 'no_auto_selection')",
            name="ck_training_run_comparisons_selection_policy",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_releases.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    primary_metric: Mapped[str] = mapped_column(String(32), nullable=False)
    primary_split: Mapped[str] = mapped_column(String(32), nullable=False)
    selection_policy: Mapped[str] = mapped_column(String(64), nullable=False)
    selected_training_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("training_runs.id"), nullable=True, index=True
    )
    comparison_summary: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    warnings: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    entries: Mapped[list["TrainingRunComparisonEntryModel"]] = relationship(back_populates="comparison")
