from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from blueberry_microid.infrastructure.db.models.base import Base
from blueberry_microid.infrastructure.db.models.column_types import PortableJSON
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blueberry_microid.infrastructure.db.models.image_feature_extraction_run import (
        ImageFeatureExtractionRunModel,
    )


class ImageFeatureVectorModel(Base):
    """One Petri or micro image's persisted non-deep feature vector for a
    specific ImageFeatureExtractionRun."""

    __tablename__ = "image_feature_vectors"
    __table_args__ = (
        UniqueConstraint(
            "feature_extraction_run_id",
            "dataset_split_item_id",
            "modality",
            name="uq_image_feature_vectors_run_split_item_modality",
        ),
        CheckConstraint("split IN ('train', 'validation', 'test')", name="ck_image_feature_vectors_split"),
        CheckConstraint("modality IN ('petri', 'micro')", name="ck_image_feature_vectors_modality"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feature_extraction_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("image_feature_extraction_runs.id"), nullable=False, index=True
    )
    dataset_release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_releases.id"), nullable=False, index=True
    )
    dataset_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_items.id"), nullable=False, index=True
    )
    dataset_split_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_split_items.id"), nullable=False, index=True
    )
    split: Mapped[str] = mapped_column(String(32), nullable=False)
    modality: Mapped[str] = mapped_column(String(32), nullable=False)
    image_path: Mapped[str] = mapped_column(Text, nullable=False)
    features: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    preprocessing: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    extraction_version: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    feature_extraction_run: Mapped["ImageFeatureExtractionRunModel"] = relationship(back_populates="vectors")
