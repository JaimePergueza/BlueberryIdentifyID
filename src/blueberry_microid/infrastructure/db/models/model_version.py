from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from blueberry_microid.domain.enums.model_type import ModelType
from blueberry_microid.infrastructure.db.models.base import Base
from blueberry_microid.infrastructure.db.models.enums import model_type_enum

if TYPE_CHECKING:
    from blueberry_microid.infrastructure.db.models.analysis_run import AnalysisRunModel


class ModelVersionModel(Base):
    """A registered, traceable version of an inference engine (mock, pytorch or external)."""

    __tablename__ = "model_versions"
    __table_args__ = (UniqueConstraint("name", "version", name="uq_model_versions_name_version"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    model_type: Mapped[ModelType] = mapped_column(model_type_enum, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    analysis_runs: Mapped[list["AnalysisRunModel"]] = relationship(back_populates="model_version")
