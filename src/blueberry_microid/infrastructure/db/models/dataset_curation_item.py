from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from blueberry_microid.domain.enums.dataset_curation_status import DatasetCurationStatus
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision
from blueberry_microid.infrastructure.db.models.base import Base
from blueberry_microid.infrastructure.db.models.column_types import PortableJSON
from blueberry_microid.infrastructure.db.models.enums import (
    dataset_curation_status_enum,
    predicted_label_enum,
    review_decision_enum,
)

if TYPE_CHECKING:
    from blueberry_microid.infrastructure.db.models.analysis_run import AnalysisRunModel
    from blueberry_microid.infrastructure.db.models.dataset_curation_run import DatasetCurationRunModel
    from blueberry_microid.infrastructure.db.models.human_review import HumanReviewModel
    from blueberry_microid.infrastructure.db.models.micro_image import MicroImageModel
    from blueberry_microid.infrastructure.db.models.petri_image import PetriImageModel
    from blueberry_microid.infrastructure.db.models.prediction import PredictionModel
    from blueberry_microid.infrastructure.db.models.sample import SampleModel


class DatasetCurationItemModel(Base):
    __tablename__ = "dataset_curation_items"
    __table_args__ = (
        UniqueConstraint("curation_run_id", "analysis_run_id", name="uq_dataset_curation_items_run_analysis_run"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    curation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_curation_runs.id"), nullable=False, index=True
    )
    sample_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("samples.id"), nullable=True)
    analysis_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=True, index=True
    )
    prediction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("predictions.id"), nullable=True
    )
    human_review_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("human_reviews.id"), nullable=True
    )
    petri_image_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("petri_images.id"), nullable=True
    )
    micro_image_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("micro_images.id"), nullable=True
    )
    automatic_label: Mapped[Optional[PredictedLabel]] = mapped_column(predicted_label_enum, nullable=True)
    final_label: Mapped[Optional[PredictedLabel]] = mapped_column(predicted_label_enum, nullable=True)
    review_decision: Mapped[Optional[ReviewDecision]] = mapped_column(review_decision_enum, nullable=True)
    curation_status: Mapped[DatasetCurationStatus] = mapped_column(dataset_curation_status_enum, nullable=False)
    exclusion_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    provenance: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    feature_summary: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    quality_summary: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    curation_run: Mapped["DatasetCurationRunModel"] = relationship(back_populates="items")
    sample: Mapped[Optional["SampleModel"]] = relationship()
    analysis_run: Mapped[Optional["AnalysisRunModel"]] = relationship()
    prediction: Mapped[Optional["PredictionModel"]] = relationship()
    human_review: Mapped[Optional["HumanReviewModel"]] = relationship()
    petri_image: Mapped[Optional["PetriImageModel"]] = relationship()
    micro_image: Mapped[Optional["MicroImageModel"]] = relationship()

