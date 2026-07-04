from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from blueberry_microid.infrastructure.db.models.base import Base
from blueberry_microid.infrastructure.db.models.column_types import PortableJSON

_ARTIFACT_KINDS = (
    "planned_weights", "planned_metrics", "planned_predictions", "planned_logs",
    "planned_run_dir", "planned_config", "planned_manifest",
    "actual_weights", "actual_metrics", "actual_predictions", "actual_logs", "actual_manifest",
    "other",
)
_ARTIFACT_STATES = ("planned", "registered", "missing", "forbidden", "ignored", "deleted", "unknown")
_LOCATION_TYPES = ("local_path", "external_uri", "relative_path", "unresolved")


class DetectionTrainingArtifactRecordModel(Base):
    __tablename__ = "detection_training_artifact_records"
    __table_args__ = (
        CheckConstraint(
            "artifact_kind IN (" + ", ".join(f"'{v}'" for v in _ARTIFACT_KINDS) + ")",
            name="ck_detection_training_artifact_records_kind",
        ),
        CheckConstraint(
            "artifact_state IN (" + ", ".join(f"'{v}'" for v in _ARTIFACT_STATES) + ")",
            name="ck_detection_training_artifact_records_state",
        ),
        CheckConstraint(
            "location_type IN (" + ", ".join(f"'{v}'" for v in _LOCATION_TYPES) + ")",
            name="ck_detection_training_artifact_records_location_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_training_artifact_policies.id"), nullable=False, index=True
    )
    detection_training_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_training_runs.id"), nullable=False, index=True
    )
    artifact_kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    artifact_state: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    location_type: Mapped[str] = mapped_column(String(16), nullable=False)
    artifact_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    relative_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    external_uri: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_extension: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    checksum_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    artifact_metadata: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
