from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from blueberry_microid.domain.enums.dataset_curation_run_status import DatasetCurationRunStatus
from blueberry_microid.infrastructure.db.models.base import Base
from blueberry_microid.infrastructure.db.models.column_types import PortableJSON
from blueberry_microid.infrastructure.db.models.enums import dataset_curation_run_status_enum

if TYPE_CHECKING:
    from blueberry_microid.infrastructure.db.models.dataset_curation_item import DatasetCurationItemModel
    from blueberry_microid.infrastructure.db.models.dataset_snapshot import DatasetSnapshotModel


class DatasetCurationRunModel(Base):
    __tablename__ = "dataset_curation_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[DatasetCurationRunStatus] = mapped_column(
        dataset_curation_run_status_enum,
        nullable=False,
        server_default=DatasetCurationRunStatus.COMPLETED.value,
    )
    policy: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    total_candidates_scanned: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    included_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    excluded_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_snapshots.id"), nullable=True, index=True
    )
    issues: Mapped[Optional[list]] = mapped_column(PortableJSON, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_snapshot: Mapped[Optional["DatasetSnapshotModel"]] = relationship()
    items: Mapped[list["DatasetCurationItemModel"]] = relationship(back_populates="curation_run")

