from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.infrastructure.db.models.base import Base
from blueberry_microid.infrastructure.db.models.enums import (
    dataset_split_enum,
    predicted_label_enum as ground_truth_label_enum,
)

if TYPE_CHECKING:
    from blueberry_microid.infrastructure.db.models.dataset_item import DatasetItemModel
    from blueberry_microid.infrastructure.db.models.dataset_release import DatasetReleaseModel
    from blueberry_microid.infrastructure.db.models.sample import SampleModel


class DatasetSplitItemModel(Base):
    """One DatasetItem's train/validation/test assignment within a
    DatasetRelease. A given DatasetItem can appear at most once per
    DatasetRelease (enforced by the unique constraint below)."""

    __tablename__ = "dataset_split_items"
    __table_args__ = (
        UniqueConstraint(
            "dataset_release_id",
            "dataset_item_id",
            name="uq_dataset_split_items_release_item",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_releases.id"), nullable=False, index=True
    )
    dataset_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_items.id"), nullable=False, index=True
    )
    sample_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("samples.id"), nullable=False)
    split: Mapped[DatasetSplit] = mapped_column(dataset_split_enum, nullable=False)
    ground_truth_label: Mapped[Optional[PredictedLabel]] = mapped_column(ground_truth_label_enum, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    dataset_release: Mapped["DatasetReleaseModel"] = relationship(back_populates="split_items")
    dataset_item: Mapped["DatasetItemModel"] = relationship()
    sample: Mapped["SampleModel"] = relationship()
