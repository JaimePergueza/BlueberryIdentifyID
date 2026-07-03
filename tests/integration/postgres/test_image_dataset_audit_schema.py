import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from blueberry_microid.infrastructure.db.models import ImageDatasetAuditIssueModel, ImageDatasetAuditRunModel
from tests.integration.postgres.test_dataset_release_schema import _create_dataset_item, _create_release

pytestmark = pytest.mark.postgres


def _create_audit_run(pg_session, dataset_release_id, **overrides) -> ImageDatasetAuditRunModel:
    defaults = dict(
        dataset_release_id=dataset_release_id,
        status="passed",
        is_passed=True,
        total_items=1,
        total_petri_images=1,
        total_micro_images=1,
        checked_petri_images=1,
        checked_micro_images=1,
        failed_petri_images=0,
        failed_micro_images=0,
        warning_count=0,
        error_count=0,
        summary={"error_count": 0, "warning_count": 0, "contains_model_metrics": False, "contains_taxonomy": False},
        format_distribution={"JPEG": 1},
        color_mode_distribution={"RGB": 1},
        dimension_distribution={"under_256": 1},
        file_size_distribution={"under_100kb": 1},
    )
    defaults.update(overrides)
    audit_run = ImageDatasetAuditRunModel(**defaults)
    pg_session.add(audit_run)
    pg_session.flush()
    return audit_run


def test_alembic_created_image_dataset_audit_tables(pg_session):
    rows = (
        pg_session.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('image_dataset_audit_runs', 'image_dataset_audit_issues')
                ORDER BY table_name
                """
            )
        )
        .scalars()
        .all()
    )

    assert rows == ["image_dataset_audit_issues", "image_dataset_audit_runs"]


def test_image_dataset_audit_run_status_check_constraint_rejects_unknown_value(pg_session):
    item = _create_dataset_item(pg_session, sample_code="S-PG-IMGAUDIT-BADSTATUS")
    release = _create_release(pg_session, item.dataset_snapshot_id)

    with pytest.raises(IntegrityError):
        _create_audit_run(pg_session, release.id, status="not_a_real_status")


def test_image_dataset_audit_issue_severity_check_constraint_rejects_unknown_value(pg_session):
    item = _create_dataset_item(pg_session, sample_code="S-PG-IMGAUDIT-BADSEVERITY")
    release = _create_release(pg_session, item.dataset_snapshot_id)
    audit_run = _create_audit_run(pg_session, release.id)

    issue = ImageDatasetAuditIssueModel(
        audit_run_id=audit_run.id,
        severity="not_a_real_severity",
        modality="petri",
        code="image_missing",
        message="test",
    )
    pg_session.add(issue)

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_image_dataset_audit_issue_modality_check_constraint_rejects_unknown_value(pg_session):
    item = _create_dataset_item(pg_session, sample_code="S-PG-IMGAUDIT-BADMODALITY")
    release = _create_release(pg_session, item.dataset_snapshot_id)
    audit_run = _create_audit_run(pg_session, release.id)

    issue = ImageDatasetAuditIssueModel(
        audit_run_id=audit_run.id,
        severity="error",
        modality="not_a_real_modality",
        code="image_missing",
        message="test",
    )
    pg_session.add(issue)

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_image_dataset_audit_run_json_columns_round_trip_as_jsonb(pg_session):
    item = _create_dataset_item(pg_session, sample_code="S-PG-IMGAUDIT-JSON")
    release = _create_release(pg_session, item.dataset_snapshot_id)
    audit_run = _create_audit_run(pg_session, release.id)
    pg_session.refresh(audit_run)

    assert audit_run.summary["contains_taxonomy"] is False
    assert audit_run.format_distribution["JPEG"] == 1
    assert audit_run.dimension_distribution["under_256"] == 1

    column_type = pg_session.execute(
        text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'image_dataset_audit_runs' AND column_name = 'summary'"
        )
    ).scalar_one()
    assert column_type == "jsonb"


def test_image_dataset_audit_issue_details_round_trips_as_jsonb(pg_session):
    item = _create_dataset_item(pg_session, sample_code="S-PG-IMGAUDIT-ISSUEJSON")
    release = _create_release(pg_session, item.dataset_snapshot_id)
    audit_run = _create_audit_run(pg_session, release.id)

    issue = ImageDatasetAuditIssueModel(
        audit_run_id=audit_run.id,
        severity="warning",
        modality="micro",
        dataset_item_id=item.id,
        code="image_too_small",
        message="micro image is smaller than the minimum",
        details={"width": 10, "height": 10},
    )
    pg_session.add(issue)
    pg_session.flush()
    pg_session.refresh(issue)

    assert issue.details["width"] == 10


def test_image_dataset_audit_run_foreign_key_to_dataset_release_is_enforced(pg_session):
    audit_run = ImageDatasetAuditRunModel(
        dataset_release_id=uuid.uuid4(),
        status="passed",
        is_passed=True,
        total_items=0,
        total_petri_images=0,
        total_micro_images=0,
        checked_petri_images=0,
        checked_micro_images=0,
        failed_petri_images=0,
        failed_micro_images=0,
        warning_count=0,
        error_count=0,
        summary={},
        format_distribution={},
        color_mode_distribution={},
        dimension_distribution={},
        file_size_distribution={},
    )
    pg_session.add(audit_run)

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_image_dataset_audit_issue_foreign_keys_are_enforced(pg_session):
    item = _create_dataset_item(pg_session, sample_code="S-PG-IMGAUDIT-FK")
    release = _create_release(pg_session, item.dataset_snapshot_id)
    audit_run = _create_audit_run(pg_session, release.id)

    issue = ImageDatasetAuditIssueModel(
        audit_run_id=audit_run.id,
        severity="error",
        modality="petri",
        dataset_item_id=uuid.uuid4(),
        code="image_missing",
        message="test",
    )
    pg_session.add(issue)

    with pytest.raises(IntegrityError):
        pg_session.flush()
