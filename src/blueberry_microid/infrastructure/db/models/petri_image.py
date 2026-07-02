from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from blueberry_microid.infrastructure.db.models.base import Base

if TYPE_CHECKING:
    from blueberry_microid.infrastructure.db.models.analysis_run import AnalysisRunModel
    from blueberry_microid.infrastructure.db.models.sample import SampleModel


class PetriImageModel(Base):
    """A macro photograph of the Petri dish where microbial growth is observed.

    Never a photograph of the blueberry fruit itself.
    """

    __tablename__ = "petri_images"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sample_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("samples.id"), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    captured_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    culture_medium: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    incubation_temperature_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    incubation_time_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    seeding_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    observed_colony_color: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    observed_colony_shape: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    observed_colony_margin: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    observed_colony_texture: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    sample: Mapped["SampleModel"] = relationship(back_populates="petri_images")
    analysis_runs: Mapped[list["AnalysisRunModel"]] = relationship(back_populates="petri_image")
