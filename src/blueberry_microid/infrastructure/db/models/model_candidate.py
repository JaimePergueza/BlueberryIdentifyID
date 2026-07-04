from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from blueberry_microid.infrastructure.db.models.base import Base
from blueberry_microid.infrastructure.db.models.column_types import PortableJSON

_KINDS = ("smoke_yolo", "experimental_yolo", "classical_baseline", "other")
_STATUSES = ("created", "evaluated", "blocked", "promoted", "archived", "failed")


class ModelCandidateModel(Base):
    __tablename__ = "model_candidates"
    __table_args__ = (
        CheckConstraint("candidate_kind IN (" + ", ".join(f"'{v}'" for v in _KINDS) + ")", name="ck_mc_kind"),
        CheckConstraint("status IN (" + ", ".join(f"'{v}'" for v in _STATUSES) + ")", name="ck_mc_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    local_yolo_training_execution_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_training_execution_runs.id"), nullable=True, index=True
    )
    detection_training_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_training_runs.id"), nullable=True, index=True
    )
    model_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_versions.id"), nullable=True, index=True
    )
    candidate_kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    model_artifact_path: Mapped[str] = mapped_column(Text, nullable=False)
    model_artifact_checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    model_artifact_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    metrics_artifact_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config_artifact_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_summary: Mapped[dict] = mapped_column(PortableJSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
