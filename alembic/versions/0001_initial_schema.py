"""Initial schema: samples, petri_images, micro_images, model_versions, analysis_runs, predictions, human_reviews

Revision ID: 0001
Revises:
Create Date: 2026-07-01

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

model_type_enum = postgresql.ENUM(
    "mock", "pytorch", "external", name="model_type", create_type=False
)
analysis_status_enum = postgresql.ENUM(
    "pending", "processing", "completed", "failed", "needs_review",
    name="analysis_status", create_type=False,
)
predicted_label_enum = postgresql.ENUM(
    "no_evident_growth",
    "suspicious_growth",
    "probable_fungal_growth",
    "probable_bacterial_growth",
    "inconclusive",
    name="predicted_label",
    create_type=False,
)
review_decision_enum = postgresql.ENUM(
    "confirmed",
    "corrected",
    "marked_inconclusive",
    "rejected_invalid_sample",
    name="review_decision",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    model_type_enum.create(bind, checkfirst=True)
    analysis_status_enum.create(bind, checkfirst=True)
    predicted_label_enum.create(bind, checkfirst=True)
    review_decision_enum.create(bind, checkfirst=True)

    op.create_table(
        "samples",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sample_code", sa.String(length=64), nullable=False),
        sa.Column("product", sa.String(length=32), nullable=False, server_default="blueberry"),
        sa.Column("lot_code", sa.String(length=64), nullable=True),
        sa.Column("origin", sa.String(length=255), nullable=True),
        sa.Column("collection_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("sample_code", name="uq_samples_sample_code"),
    )

    op.create_table(
        "model_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("model_type", model_type_enum, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("name", "version", name="uq_model_versions_name_version"),
    )

    op.create_table(
        "petri_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sample_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("samples.id"), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("culture_medium", sa.String(length=255), nullable=True),
        sa.Column("incubation_temperature_c", sa.Float(), nullable=True),
        sa.Column("incubation_time_hours", sa.Float(), nullable=True),
        sa.Column("seeding_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observed_colony_color", sa.String(length=255), nullable=True),
        sa.Column("observed_colony_shape", sa.String(length=255), nullable=True),
        sa.Column("observed_colony_margin", sa.String(length=255), nullable=True),
        sa.Column("observed_colony_texture", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_petri_images_sample_id", "petri_images", ["sample_id"])

    op.create_table(
        "micro_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sample_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("samples.id"), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("magnification", sa.String(length=64), nullable=True),
        sa.Column("microscope_type", sa.String(length=255), nullable=True),
        sa.Column("staining_method", sa.String(length=255), nullable=True),
        sa.Column("preparation_method", sa.String(length=255), nullable=True),
        sa.Column("observed_structures", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_micro_images_sample_id", "micro_images", ["sample_id"])

    op.create_table(
        "analysis_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sample_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("samples.id"), nullable=False),
        sa.Column(
            "petri_image_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("petri_images.id"), nullable=False
        ),
        sa.Column(
            "micro_image_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("micro_images.id"), nullable=False
        ),
        sa.Column(
            "model_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("model_versions.id"),
            nullable=False,
        ),
        sa.Column("status", analysis_status_enum, nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_analysis_runs_sample_id", "analysis_runs", ["sample_id"])
    op.create_index("ix_analysis_runs_petri_image_id", "analysis_runs", ["petri_image_id"])
    op.create_index("ix_analysis_runs_micro_image_id", "analysis_runs", ["micro_image_id"])
    op.create_index("ix_analysis_runs_model_version_id", "analysis_runs", ["model_version_id"])

    op.create_table(
        "predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analysis_runs.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("predicted_label", predicted_label_enum, nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("class_probabilities", postgresql.JSONB(), nullable=True),
        sa.Column("technical_observation", sa.Text(), nullable=True),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_predictions_confidence_score_range",
        ),
    )

    op.create_table(
        "human_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("analysis_runs.id"), nullable=False
        ),
        sa.Column("reviewer_name", sa.String(length=255), nullable=False),
        sa.Column("review_decision", review_decision_enum, nullable=False),
        sa.Column("corrected_label", predicted_label_enum, nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "review_decision != 'corrected' OR corrected_label IS NOT NULL",
            name="ck_human_reviews_corrected_label_required",
        ),
    )
    op.create_index("ix_human_reviews_analysis_run_id", "human_reviews", ["analysis_run_id"])


def downgrade() -> None:
    op.drop_table("human_reviews")
    op.drop_table("predictions")
    op.drop_index("ix_analysis_runs_model_version_id", table_name="analysis_runs")
    op.drop_index("ix_analysis_runs_micro_image_id", table_name="analysis_runs")
    op.drop_index("ix_analysis_runs_petri_image_id", table_name="analysis_runs")
    op.drop_index("ix_analysis_runs_sample_id", table_name="analysis_runs")
    op.drop_table("analysis_runs")
    op.drop_index("ix_micro_images_sample_id", table_name="micro_images")
    op.drop_table("micro_images")
    op.drop_index("ix_petri_images_sample_id", table_name="petri_images")
    op.drop_table("petri_images")
    op.drop_table("model_versions")
    op.drop_table("samples")

    bind = op.get_bind()
    review_decision_enum.drop(bind, checkfirst=True)
    predicted_label_enum.drop(bind, checkfirst=True)
    analysis_status_enum.drop(bind, checkfirst=True)
    model_type_enum.drop(bind, checkfirst=True)
