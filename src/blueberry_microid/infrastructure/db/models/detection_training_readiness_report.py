from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from blueberry_microid.infrastructure.db.models.base import Base
from blueberry_microid.infrastructure.db.models.column_types import PortableJSON


class DetectionTrainingReadinessReportModel(Base):
    """A persisted verdict on whether a DetectionTrainingRun is technically
    ready for a future real training phase.

    `is_ready=true` never means scientific validity or a trained model — see
    the entity docstring.
    """

    __tablename__ = "detection_training_readiness_reports"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('ready_for_training', 'needs_more_annotations', 'blocked_by_quality', "
            "'blocked_by_environment', 'blocked_by_contract', 'blocked_by_configuration')",
            name="ck_detection_training_readiness_reports_decision",
        ),
        CheckConstraint(
            "status IN ('ready', 'warning', 'blocked', 'failed')",
            name="ck_detection_training_readiness_reports_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    detection_training_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_training_runs.id"), nullable=False, index=True
    )
    annotation_bundle_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("annotation_bundle_runs.id"), nullable=False, index=True
    )
    annotation_quality_gate_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("annotation_quality_gate_runs.id"), nullable=True, index=True
    )
    dataset_release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_releases.id"), nullable=False, index=True
    )
    petri_annotation_export_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("petri_annotation_export_runs.id"), nullable=False, index=True
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    is_ready: Mapped[bool] = mapped_column(Boolean, nullable=False)
    config: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    data_summary: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    split_summary: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    quality_summary: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    environment_summary: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    contract_summary: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    risk_summary: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    recommendation_summary: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False)
    info_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
