from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from blueberry_microid.domain.enums.analysis_status import AnalysisStatus
from blueberry_microid.infrastructure.db.models.base import Base
from blueberry_microid.infrastructure.db.models.enums import analysis_status_enum

if TYPE_CHECKING:
    from blueberry_microid.infrastructure.db.models.human_review import HumanReviewModel
    from blueberry_microid.infrastructure.db.models.micro_image import MicroImageModel
    from blueberry_microid.infrastructure.db.models.model_version import ModelVersionModel
    from blueberry_microid.infrastructure.db.models.petri_image import PetriImageModel
    from blueberry_microid.infrastructure.db.models.prediction import PredictionModel
    from blueberry_microid.infrastructure.db.models.sample import SampleModel


class AnalysisRunModel(Base):
    """A single, explicit execution of the multimodal inference pipeline.

    Always references exactly one PetriImage and one MicroImage. The
    application layer is responsible for guaranteeing (via the domain
    factory `AnalysisRun.create`) that both belong to the same Sample before
    a row is persisted here.
    """

    __tablename__ = "analysis_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sample_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("samples.id"), nullable=False, index=True
    )
    petri_image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("petri_images.id"), nullable=False, index=True
    )
    micro_image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("micro_images.id"), nullable=False, index=True
    )
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_versions.id"), nullable=False, index=True
    )
    status: Mapped[AnalysisStatus] = mapped_column(
        analysis_status_enum, nullable=False, server_default=AnalysisStatus.PENDING.value
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    sample: Mapped["SampleModel"] = relationship(back_populates="analysis_runs")
    petri_image: Mapped["PetriImageModel"] = relationship(back_populates="analysis_runs")
    micro_image: Mapped["MicroImageModel"] = relationship(back_populates="analysis_runs")
    model_version: Mapped["ModelVersionModel"] = relationship(back_populates="analysis_runs")
    prediction: Mapped[Optional["PredictionModel"]] = relationship(back_populates="analysis_run", uselist=False)
    human_reviews: Mapped[list["HumanReviewModel"]] = relationship(back_populates="analysis_run")
