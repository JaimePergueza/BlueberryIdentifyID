from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision
from blueberry_microid.infrastructure.db.models.base import Base
from blueberry_microid.infrastructure.db.models.enums import (
    predicted_label_enum as corrected_label_enum,
    review_decision_enum,
)

if TYPE_CHECKING:
    from blueberry_microid.infrastructure.db.models.analysis_run import AnalysisRunModel


class HumanReviewModel(Base):
    """An expert's review of an AnalysisRun's Prediction.

    Never overwrites the original Prediction row. Multiple reviews per
    AnalysisRun are allowed over time, to preserve full audit history — but
    a partial unique index guarantees at most one of them has
    `is_final=True` at any given time.
    """

    __tablename__ = "human_reviews"
    __table_args__ = (
        CheckConstraint(
            "review_decision != 'corrected' OR corrected_label IS NOT NULL",
            name="ck_human_reviews_corrected_label_required",
        ),
        Index(
            "uq_human_reviews_one_final_per_run",
            "analysis_run_id",
            unique=True,
            postgresql_where=text("is_final = true"),
            sqlite_where=text("is_final = 1"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False, index=True
    )
    reviewer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    review_decision: Mapped[ReviewDecision] = mapped_column(review_decision_enum, nullable=False)
    corrected_label: Mapped[Optional[PredictedLabel]] = mapped_column(corrected_label_enum, nullable=True)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    analysis_run: Mapped["AnalysisRunModel"] = relationship(back_populates="human_reviews")
