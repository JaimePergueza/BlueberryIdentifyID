from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from blueberry_microid.infrastructure.db.models.base import Base
from blueberry_microid.infrastructure.db.models.column_types import PortableJSON

_DECISIONS = (
    "smoke_only", "not_evaluable", "not_promotable", "promotable_with_warnings",
    "promotable", "blocked_by_policy", "failed_evaluation",
)


class ModelPromotionGateRunModel(Base):
    __tablename__ = "model_promotion_gate_runs"
    __table_args__ = (
        CheckConstraint("decision IN (" + ", ".join(f"'{v}'" for v in _DECISIONS) + ")", name="ck_mpgr_decision"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_candidates.id"), nullable=False, index=True
    )
    model_evaluation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_evaluation_runs.id"), nullable=False, index=True
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    gate_summary: Mapped[dict] = mapped_column(PortableJSON, nullable=False, default=dict)
    blocking_reasons: Mapped[list] = mapped_column(PortableJSON, nullable=False, default=list)
    required_thresholds: Mapped[dict] = mapped_column(PortableJSON, nullable=False, default=dict)
    observed_metrics: Mapped[dict] = mapped_column(PortableJSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
