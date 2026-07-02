from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from blueberry_microid.infrastructure.db.models.base import Base

if TYPE_CHECKING:
    from blueberry_microid.infrastructure.db.models.analysis_run import AnalysisRunModel
    from blueberry_microid.infrastructure.db.models.micro_image import MicroImageModel
    from blueberry_microid.infrastructure.db.models.petri_image import PetriImageModel


class SampleModel(Base):
    """A blueberry sample submitted for microbiological screening."""

    __tablename__ = "samples"
    __table_args__ = (UniqueConstraint("sample_code", name="uq_samples_sample_code"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sample_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    product: Mapped[str] = mapped_column(String(32), nullable=False, server_default="blueberry")
    lot_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    origin: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    collection_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    petri_images: Mapped[list["PetriImageModel"]] = relationship(back_populates="sample")
    micro_images: Mapped[list["MicroImageModel"]] = relationship(back_populates="sample")
    analysis_runs: Mapped[list["AnalysisRunModel"]] = relationship(back_populates="sample")
