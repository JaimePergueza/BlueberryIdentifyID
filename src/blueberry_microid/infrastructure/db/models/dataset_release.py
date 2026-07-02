from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from blueberry_microid.infrastructure.db.models.base import Base
from blueberry_microid.infrastructure.db.models.column_types import PortableJSON

if TYPE_CHECKING:
    from blueberry_microid.infrastructure.db.models.dataset_snapshot import DatasetSnapshotModel
    from blueberry_microid.infrastructure.db.models.dataset_split_item import DatasetSplitItemModel


class DatasetReleaseModel(Base):
    """A reproducible train/validation/test partition of a DatasetSnapshot."""

    __tablename__ = "dataset_releases"
    __table_args__ = (
        CheckConstraint(
            "split_strategy IN ('by_sample', 'by_lot', 'by_origin_lot')",
            name="ck_dataset_releases_split_strategy",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_snapshots.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    split_strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    random_seed: Mapped[int] = mapped_column(Integer, nullable=False)
    train_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    validation_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    test_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    train_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    validation_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    test_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    label_distribution: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    split_distribution: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    dataset_snapshot: Mapped["DatasetSnapshotModel"] = relationship()
    split_items: Mapped[list["DatasetSplitItemModel"]] = relationship(back_populates="dataset_release")
