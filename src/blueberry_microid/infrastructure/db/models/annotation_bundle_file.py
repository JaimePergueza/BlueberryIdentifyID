from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from blueberry_microid.infrastructure.db.models.base import Base


class AnnotationBundleFileModel(Base):
    __tablename__ = "annotation_bundle_files"
    __table_args__ = (
        CheckConstraint(
            "file_role IN ('coco_annotations', 'yolo_label', 'blueberry_manifest', 'dataset_yaml', "
            "'readme', 'bundle_manifest', 'copied_image')",
            name="ck_annotation_bundle_files_role",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bundle_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("annotation_bundle_runs.id"), nullable=False, index=True
    )
    file_role: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    relative_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    checksum_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
