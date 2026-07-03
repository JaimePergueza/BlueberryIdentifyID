from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from blueberry_microid.infrastructure.db.models.base import Base
from blueberry_microid.infrastructure.db.models.column_types import PortableJSON


class DetectionTrainingEnvironmentSpecModel(Base):
    """A persisted specification/evaluation of a future real training
    environment.

    `is_environment_ready=true` never means a real training environment was
    provisioned, never that ultralytics/torch were installed, and never that
    training was executed.
    """

    __tablename__ = "detection_training_environment_specs"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('environment_ready', 'needs_manual_setup', 'blocked_by_missing_requirements', "
            "'blocked_by_policy', 'blocked_by_unsupported_platform', 'blocked_by_storage_policy', "
            "'blocked_by_dependency_policy')",
            name="ck_detection_training_environment_specs_decision",
        ),
        CheckConstraint(
            "status IN ('ready', 'warning', 'blocked', 'failed')",
            name="ck_detection_training_environment_specs_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    detection_training_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_training_runs.id"), nullable=False, index=True
    )
    readiness_report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_training_readiness_reports.id"), nullable=False, index=True
    )
    annotation_bundle_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("annotation_bundle_runs.id"), nullable=False, index=True
    )
    dataset_release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_releases.id"), nullable=False, index=True
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    is_environment_ready: Mapped[bool] = mapped_column(Boolean, nullable=False)
    config: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    detected_environment: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    dependency_policy: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    hardware_policy: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    artifact_policy: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    execution_policy: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    setup_instructions: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    safe_check_summary: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
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
