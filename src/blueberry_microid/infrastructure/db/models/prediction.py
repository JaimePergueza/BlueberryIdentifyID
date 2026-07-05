from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.infrastructure.db.models.base import Base
from blueberry_microid.infrastructure.db.models.column_types import PortableJSON
from blueberry_microid.infrastructure.db.models.enums import predicted_label_enum

if TYPE_CHECKING:
    from blueberry_microid.infrastructure.db.models.analysis_run import AnalysisRunModel


class PredictionModel(Base):
    """The preliminary, non-diagnostic result of one AnalysisRun.

    `predicted_label` is a broad visual category — never a species/genus.
    One AnalysisRun has at most one Prediction; re-processing creates a new
    AnalysisRun instead of overwriting this row.
    """

    __tablename__ = "predictions"
    __table_args__ = (
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_predictions_confidence_score_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False, unique=True
    )
    predicted_label: Mapped[PredictedLabel] = mapped_column(predicted_label_enum, nullable=False)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    class_probabilities: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    technical_observation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    feature_summary: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    quality_summary: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    decision_trace: Mapped[Optional[list]] = mapped_column(PortableJSON, nullable=True)
    warnings: Mapped[Optional[list]] = mapped_column(PortableJSON, nullable=True)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    analysis_run: Mapped["AnalysisRunModel"] = relationship(back_populates="prediction")
