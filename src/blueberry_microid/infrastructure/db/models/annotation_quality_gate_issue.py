from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from blueberry_microid.infrastructure.db.models.base import Base
from blueberry_microid.infrastructure.db.models.column_types import PortableJSON


class AnnotationQualityGateIssueModel(Base):
    __tablename__ = "annotation_quality_gate_issues"
    __table_args__ = (
        CheckConstraint("severity IN ('error', 'warning')", name="ck_annotation_quality_gate_issues_severity"),
        CheckConstraint(
            "split IS NULL OR split IN ('train', 'validation', 'test')",
            name="ck_annotation_quality_gate_issues_split",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quality_gate_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("annotation_quality_gate_runs.id"), nullable=False, index=True
    )
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    split: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    image_path: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    annotation_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
