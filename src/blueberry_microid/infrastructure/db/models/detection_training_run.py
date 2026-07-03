from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from blueberry_microid.infrastructure.db.models.base import Base
from blueberry_microid.infrastructure.db.models.column_types import PortableJSON


class DetectionTrainingRunModel(Base):
    """A persisted dry-run plan for a future object-detection training attempt.

    `status=planned` never means a model was trained — see the entity
    docstring. No model weights, image bytes, or taxonomy are stored here.
    """

    __tablename__ = "detection_training_runs"
    __table_args__ = (
        CheckConstraint("algorithm IN ('yolo_dry_run')", name="ck_detection_training_runs_algorithm"),
        CheckConstraint("mode IN ('dry_run')", name="ck_detection_training_runs_mode"),
        CheckConstraint("status IN ('planned', 'blocked', 'failed')", name="ck_detection_training_runs_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    algorithm: Mapped[str] = mapped_column(String(32), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    is_runnable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    config: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    training_plan: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    command_preview: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    dataset_summary: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    quality_gate_summary: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    expected_outputs: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    issue_count: Mapped[int] = mapped_column(Integer, nullable=False)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
