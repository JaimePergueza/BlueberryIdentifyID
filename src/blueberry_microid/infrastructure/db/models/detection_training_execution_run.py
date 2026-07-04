from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from blueberry_microid.infrastructure.db.models.base import Base
from blueberry_microid.infrastructure.db.models.column_types import PortableJSON

_STATUSES = ("blocked", "manual_required", "ready_to_execute", "failed")
_DECISIONS = (
    "blocked_by_prerequisites",
    "blocked_by_ci",
    "blocked_by_repository_safety",
    "blocked_by_artifact_policy",
    "blocked_by_environment",
    "blocked_by_readiness",
    "blocked_by_configuration",
    "manual_confirmation_required",
    "ready_for_manual_execution",
)
_MODES = ("scaffold_only", "manual_gate")


class DetectionTrainingExecutionRunModel(Base):
    """A persisted execution-gate evaluation. `is_executable=true` never
    appears in this phase — see the entity docstring.
    """

    __tablename__ = "detection_training_execution_runs"
    __table_args__ = (
        CheckConstraint("status IN (" + ", ".join(f"'{v}'" for v in _STATUSES) + ")", name="ck_dtex_runs_status"),
        CheckConstraint(
            "decision IN (" + ", ".join(f"'{v}'" for v in _DECISIONS) + ")", name="ck_dtex_runs_decision"
        ),
        CheckConstraint("mode IN (" + ", ".join(f"'{v}'" for v in _MODES) + ")", name="ck_dtex_runs_mode"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    detection_training_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_training_runs.id"), nullable=False, index=True
    )
    readiness_report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_training_readiness_reports.id"), nullable=False, index=True
    )
    environment_spec_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_training_environment_specs.id"), nullable=False, index=True
    )
    artifact_policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_training_artifact_policies.id"), nullable=False, index=True
    )
    annotation_bundle_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("annotation_bundle_runs.id"), nullable=False, index=True
    )
    dataset_release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_releases.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    is_executable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    config: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    prerequisite_summary: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    repository_safety_summary: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    execution_plan: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    command_preview: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    expected_outputs: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
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
