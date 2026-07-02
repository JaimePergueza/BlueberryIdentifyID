from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision
from blueberry_microid.infrastructure.db.models.base import Base
from blueberry_microid.infrastructure.db.models.enums import (
    predicted_label_enum as ground_truth_label_enum,
    review_decision_enum,
)

if TYPE_CHECKING:
    from blueberry_microid.infrastructure.db.models.analysis_run import AnalysisRunModel
    from blueberry_microid.infrastructure.db.models.dataset_snapshot import DatasetSnapshotModel
    from blueberry_microid.infrastructure.db.models.human_review import HumanReviewModel
    from blueberry_microid.infrastructure.db.models.micro_image import MicroImageModel
    from blueberry_microid.infrastructure.db.models.petri_image import PetriImageModel
    from blueberry_microid.infrastructure.db.models.prediction import PredictionModel
    from blueberry_microid.infrastructure.db.models.sample import SampleModel


class DatasetItemModel(Base):
    """One traceable AnalysisRun reference captured in a DatasetSnapshot."""

    __tablename__ = "dataset_items"
    __table_args__ = (
        UniqueConstraint(
            "dataset_snapshot_id",
            "analysis_run_id",
            name="uq_dataset_items_snapshot_analysis_run",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_snapshots.id"), nullable=False, index=True
    )
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False, index=True
    )
    sample_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("samples.id"), nullable=False)
    petri_image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("petri_images.id"), nullable=False
    )
    micro_image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("micro_images.id"), nullable=False
    )
    prediction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("predictions.id"), nullable=False)
    final_review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("human_reviews.id"), nullable=False
    )
    ground_truth_label: Mapped[Optional[PredictedLabel]] = mapped_column(ground_truth_label_enum, nullable=True)
    source_review_decision: Mapped[ReviewDecision] = mapped_column(review_decision_enum, nullable=False)
    included: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    exclusion_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    dataset_snapshot: Mapped["DatasetSnapshotModel"] = relationship(back_populates="items")
    analysis_run: Mapped["AnalysisRunModel"] = relationship()
    sample: Mapped["SampleModel"] = relationship()
    petri_image: Mapped["PetriImageModel"] = relationship()
    micro_image: Mapped["MicroImageModel"] = relationship()
    prediction: Mapped["PredictionModel"] = relationship()
    final_review: Mapped["HumanReviewModel"] = relationship()

