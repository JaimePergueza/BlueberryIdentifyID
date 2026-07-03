import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from blueberry_microid.infrastructure.db.models import (
    DetectionTrainingReadinessIssueModel,
    DetectionTrainingReadinessReportModel,
)
from tests.integration.postgres.test_detection_training_schema import _detection_run, _persist_gate

pytestmark = pytest.mark.postgres


def _readiness_report(bundle, export_run, run, gate, detection_run, **kwargs):
    values = {
        "detection_training_run_id": detection_run.id,
        "annotation_bundle_run_id": bundle.id,
        "annotation_quality_gate_run_id": gate.id,
        "dataset_release_id": run.dataset_release_id,
        "petri_annotation_export_run_id": export_run.id,
        "decision": "ready_for_training",
        "status": "ready",
        "is_ready": True,
        "config": {"require_minimum_data": False},
        "data_summary": {"checked": False},
        "split_summary": {"checked": False},
        "quality_summary": {"bundle_status": "completed"},
        "environment_summary": {"require_gpu": False},
        "contract_summary": {"detection_training_run_status": "planned"},
        "risk_summary": {"error_codes": [], "warning_codes": []},
        "recommendation_summary": {"next_steps": []},
        "error_count": 0,
        "warning_count": 0,
        "info_count": 1,
    }
    values.update(kwargs)
    return DetectionTrainingReadinessReportModel(**values)


def _readiness_issue(report, **kwargs):
    values = {
        "readiness_report_id": report.id,
        "severity": "info",
        "code": "no_training_executed",
        "message": "no training was executed by this run or by this readiness evaluation",
        "details": None,
    }
    values.update(kwargs)
    return DetectionTrainingReadinessIssueModel(**values)


def _persist_detection_run(pg_session):
    bundle, export_run, run, gate = _persist_gate(pg_session)
    detection_run = _detection_run(bundle, export_run, run, gate)
    pg_session.add(detection_run)
    pg_session.flush()
    return bundle, export_run, run, gate, detection_run


def test_alembic_created_detection_training_readiness_tables(pg_session):
    rows = (
        pg_session.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN (
                      'detection_training_readiness_reports',
                      'detection_training_readiness_issues'
                  )
                ORDER BY table_name
                """
            )
        )
        .scalars()
        .all()
    )

    assert rows == ["detection_training_readiness_issues", "detection_training_readiness_reports"]


def test_decision_check_constraint_rejects_unknown_value(pg_session):
    bundle, export_run, run, gate, detection_run = _persist_detection_run(pg_session)
    pg_session.add(_readiness_report(bundle, export_run, run, gate, detection_run, decision="ready_to_deploy"))

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_status_check_constraint_rejects_unknown_value(pg_session):
    bundle, export_run, run, gate, detection_run = _persist_detection_run(pg_session)
    pg_session.add(_readiness_report(bundle, export_run, run, gate, detection_run, status="in_progress"))

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_severity_check_constraint_rejects_unknown_value(pg_session):
    bundle, export_run, run, gate, detection_run = _persist_detection_run(pg_session)
    report = _readiness_report(bundle, export_run, run, gate, detection_run)
    pg_session.add(report)
    pg_session.flush()
    pg_session.add(_readiness_issue(report, severity="critical"))

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_json_columns_round_trip_as_jsonb(pg_session):
    bundle, export_run, run, gate, detection_run = _persist_detection_run(pg_session)
    report = _readiness_report(
        bundle,
        export_run,
        run,
        gate,
        detection_run,
        data_summary={"total_images": 10, "min_total_images": 10},
        quality_summary={"quality_gate_is_passed": True},
    )
    pg_session.add(report)
    pg_session.flush()
    pg_session.refresh(report)

    assert report.data_summary["total_images"] == 10
    assert report.quality_summary["quality_gate_is_passed"] is True
    column_type = pg_session.execute(
        text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'detection_training_readiness_reports' AND column_name = 'data_summary'"
        )
    ).scalar_one()
    assert column_type == "jsonb"


def test_foreign_keys_are_enforced(pg_session):
    bundle, export_run, run, gate, detection_run = _persist_detection_run(pg_session)
    pg_session.add(
        _readiness_report(bundle, export_run, run, gate, detection_run, detection_training_run_id=uuid.uuid4())
    )

    with pytest.raises(IntegrityError):
        pg_session.flush()

    pg_session.rollback()
    bundle, export_run, run, gate, detection_run = _persist_detection_run(pg_session)
    report = _readiness_report(bundle, export_run, run, gate, detection_run)
    pg_session.add(report)
    pg_session.flush()
    pg_session.add(_readiness_issue(report, readiness_report_id=uuid.uuid4()))

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_annotation_quality_gate_run_id_is_nullable(pg_session):
    bundle, export_run, run, gate, detection_run = _persist_detection_run(pg_session)
    report = _readiness_report(
        bundle, export_run, run, gate, detection_run, annotation_quality_gate_run_id=None
    )
    pg_session.add(report)
    pg_session.flush()
    pg_session.refresh(report)

    assert report.annotation_quality_gate_run_id is None
