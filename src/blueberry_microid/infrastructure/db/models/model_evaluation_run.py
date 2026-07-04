from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from blueberry_microid.infrastructure.db.models.base import Base
from blueberry_microid.infrastructure.db.models.column_types import PortableJSON

_STATUSES = ("pending", "completed", "failed", "blocked")
_DECISIONS = (
    "smoke_only", "not_evaluable", "not_promotable", "promotable_with_warnings",
    "promotable", "blocked_by_policy", "failed_evaluation",
)


class ModelEvaluationRunModel(Base):
    __tablename__ = "model_evaluation_runs"
    __table_args__ = (
        CheckConstraint("status IN (" + ", ".join(f"'{v}'" for v in _STATUSES) + ")", name="ck_mer_status"),
        CheckConstraint("decision IN (" + ", ".join(f"'{v}'" for v in _DECISIONS) + ")", name="ck_mer_decision"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_candidates.id"), nullable=False, index=True
    )
    local_yolo_training_execution_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_training_execution_runs.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    metrics_summary: Mapped[dict] = mapped_column(PortableJSON, nullable=False, default=dict)
    thresholds: Mapped[dict] = mapped_column(PortableJSON, nullable=False, default=dict)
    dataset_summary: Mapped[dict] = mapped_column(PortableJSON, nullable=False, default=dict)
    artifact_summary: Mapped[dict] = mapped_column(PortableJSON, nullable=False, default=dict)
    evaluation_summary: Mapped[dict] = mapped_column(PortableJSON, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    info_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
