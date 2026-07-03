import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from blueberry_microid.infrastructure.db.models import (
    AnnotationQualityGateIssueModel,
    AnnotationQualityGateRunModel,
)
from tests.integration.postgres.test_annotation_bundle_schema import _bundle_run
from tests.integration.postgres.test_petri_annotation_export_schema import _create_export_run_with_review

pytestmark = pytest.mark.postgres


def _gate_run(bundle, export_run, run, **kwargs):
    values = {
        "annotation_bundle_run_id": bundle.id,
        "dataset_release_id": run.dataset_release_id,
        "petri_annotation_export_run_id": export_run.id,
        "status": "passed",
        "is_passed": True,
        "config": {"fail_on_empty_split": False},
        "total_images": 1,
        "total_annotations": 1,
        "train_image_count": 1,
        "validation_image_count": 0,
        "test_image_count": 0,
        "train_annotation_count": 1,
        "validation_annotation_count": 0,
        "test_annotation_count": 0,
        "error_count": 0,
        "warning_count": 0,
        "quality_summary": {"is_passed": True},
        "split_distribution": {"train": {"images": 1, "annotations": 1}},
        "bbox_statistics": {"count": 1, "min_width": 10},
        "category_distribution": {"candidate_region": 1},
    }
    values.update(kwargs)
    return AnnotationQualityGateRunModel(**values)


def _gate_issue(gate, **kwargs):
    values = {
        "quality_gate_run_id": gate.id,
        "severity": "warning",
        "code": "single_class_only",
        "message": "bundle contains a single category only",
        "split": None,
        "details": {"category_count": 1},
    }
    values.update(kwargs)
    return AnnotationQualityGateIssueModel(**values)


def _persist_bundle(pg_session):
    export_run, _, run, *_ = _create_export_run_with_review(pg_session)
    bundle = _bundle_run(export_run, run, status="completed", dry_run=False, config={"dry_run": False})
    pg_session.add(bundle)
    pg_session.flush()
    return bundle, export_run, run


def test_alembic_created_annotation_quality_gate_tables(pg_session):
    rows = (
        pg_session.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('annotation_quality_gate_runs', 'annotation_quality_gate_issues')
                ORDER BY table_name
                """
            )
        )
        .scalars()
        .all()
    )

    assert rows == ["annotation_quality_gate_issues", "annotation_quality_gate_runs"]


def test_quality_gate_status_and_severity_constraints(pg_session):
    bundle, export_run, run = _persist_bundle(pg_session)
    pg_session.add(_gate_run(bundle, export_run, run, status="training"))

    with pytest.raises(IntegrityError):
        pg_session.flush()

    pg_session.rollback()
    bundle, export_run, run = _persist_bundle(pg_session)
    gate = _gate_run(bundle, export_run, run)
    pg_session.add(gate)
    pg_session.flush()
    pg_session.add(_gate_issue(gate, severity="critical"))

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_quality_gate_json_columns_round_trip_as_jsonb(pg_session):
    bundle, export_run, run = _persist_bundle(pg_session)
    gate = _gate_run(
        bundle,
        export_run,
        run,
        quality_summary={"status": "passed", "file_checks": {"coco_annotations": True}},
    )
    pg_session.add(gate)
    pg_session.flush()
    pg_session.refresh(gate)

    assert gate.quality_summary["file_checks"]["coco_annotations"] is True
    column_type = pg_session.execute(
        text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'annotation_quality_gate_runs' AND column_name = 'quality_summary'"
        )
    ).scalar_one()
    assert column_type == "jsonb"


def test_quality_gate_foreign_keys_are_enforced(pg_session):
    bundle, export_run, run = _persist_bundle(pg_session)
    pg_session.add(_gate_run(bundle, export_run, run, annotation_bundle_run_id=uuid.uuid4()))

    with pytest.raises(IntegrityError):
        pg_session.flush()

    pg_session.rollback()
    bundle, export_run, run = _persist_bundle(pg_session)
    gate = _gate_run(bundle, export_run, run)
    pg_session.add(gate)
    pg_session.flush()
    pg_session.add(_gate_issue(gate, quality_gate_run_id=uuid.uuid4()))

    with pytest.raises(IntegrityError):
        pg_session.flush()
