from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from blueberry_microid.infrastructure.db.models.base import Base
from blueberry_microid.infrastructure.db.models.column_types import PortableJSON

if TYPE_CHECKING:
    from blueberry_microid.infrastructure.db.models.dataset_item import DatasetItemModel


class DatasetSnapshotModel(Base):
    """A frozen curated dataset version for future training."""

    __tablename__ = "dataset_snapshots"
    __table_args__ = (UniqueConstraint("name", "version", name="uq_dataset_snapshots_name_version"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    selection_criteria: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    label_distribution: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    items: Mapped[list["DatasetItemModel"]] = relationship(back_populates="dataset_snapshot")

