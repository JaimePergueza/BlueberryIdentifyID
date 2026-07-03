import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from blueberry_microid.infrastructure.db.models import (
    DetectionTrainingEnvironmentIssueModel,
    DetectionTrainingEnvironmentSpecModel,
)
from tests.integration.postgres.test_detection_training_readiness_schema import (
    _persist_detection_run,
    _readiness_report,
)

pytestmark = pytest.mark.postgres


def _environment_spec(bundle, run, detection_run, readiness, **kwargs):
    values = {
        "detection_training_run_id": detection_run.id,
        "readiness_report_id": readiness.id,
        "annotation_bundle_run_id": bundle.id,
        "dataset_release_id": run.dataset_release_id,
        "decision": "environment_ready",
        "status": "ready",
        "is_environment_ready": True,
        "config": {"allow_cpu_training": False},
        "detected_environment": {"detected_python_version": "3.10.10"},
        "dependency_policy": {"require_ultralytics": False},
        "hardware_policy": {"require_gpu": False},
        "artifact_policy": {"artifact_output_dir": "/tmp/artifacts"},
        "execution_policy": {"allow_ci_training": False},
        "setup_instructions": {"suggested_commands": []},
        "safe_check_summary": {"checks_performed": []},
        "risk_summary": {"error_codes": [], "warning_codes": []},
        "recommendation_summary": {"next_steps": []},
        "error_count": 0,
        "warning_count": 0,
        "info_count": 1,
    }
    values.update(kwargs)
    return DetectionTrainingEnvironmentSpecModel(**values)


def _environment_issue(spec, **kwargs):
    values = {
        "environment_spec_id": spec.id,
        "severity": "info",
        "code": "no_training_executed",
        "message": "no training was executed by this evaluation",
        "details": None,
    }
    values.update(kwargs)
    return DetectionTrainingEnvironmentIssueModel(**values)


def _persist_environment_spec(pg_session):
    bundle, export_run, run, gate, detection_run = _persist_detection_run(pg_session)
    readiness = _readiness_report(bundle, export_run, run, gate, detection_run)
    pg_session.add(readiness)
    pg_session.flush()
    return bundle, export_run, run, gate, detection_run, readiness


def test_alembic_created_detection_training_environment_tables(pg_session):
    rows = (
        pg_session.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN (
                      'detection_training_environment_specs',
                      'detection_training_environment_issues'
                  )
                ORDER BY table_name
                """
            )
        )
        .scalars()
        .all()
    )

    assert rows == ["detection_training_environment_issues", "detection_training_environment_specs"]


def test_decision_check_constraint_rejects_unknown_value(pg_session):
    bundle, export_run, run, gate, detection_run, readiness = _persist_environment_spec(pg_session)
    pg_session.add(_environment_spec(bundle, run, detection_run, readiness, decision="ready_to_deploy"))

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_status_check_constraint_rejects_unknown_value(pg_session):
    bundle, export_run, run, gate, detection_run, readiness = _persist_environment_spec(pg_session)
    pg_session.add(_environment_spec(bundle, run, detection_run, readiness, status="in_progress"))

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_severity_check_constraint_rejects_unknown_value(pg_session):
    bundle, export_run, run, gate, detection_run, readiness = _persist_environment_spec(pg_session)
    spec = _environment_spec(bundle, run, detection_run, readiness)
    pg_session.add(spec)
    pg_session.flush()
    pg_session.add(_environment_issue(spec, severity="critical"))

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_json_columns_round_trip_as_jsonb(pg_session):
    bundle, export_run, run, gate, detection_run, readiness = _persist_environment_spec(pg_session)
    spec = _environment_spec(
        bundle,
        run,
        detection_run,
        readiness,
        dependency_policy={"require_ultralytics": True, "target_ultralytics_version": "8.0.0"},
        hardware_policy={"require_gpu": True, "gpu_available_verified": False},
    )
    pg_session.add(spec)
    pg_session.flush()
    pg_session.refresh(spec)

    assert spec.dependency_policy["target_ultralytics_version"] == "8.0.0"
    assert spec.hardware_policy["gpu_available_verified"] is False
    column_type = pg_session.execute(
        text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'detection_training_environment_specs' AND column_name = 'dependency_policy'"
        )
    ).scalar_one()
    assert column_type == "jsonb"


def test_foreign_keys_are_enforced(pg_session):
    bundle, export_run, run, gate, detection_run, readiness = _persist_environment_spec(pg_session)
    pg_session.add(_environment_spec(bundle, run, detection_run, readiness, detection_training_run_id=uuid.uuid4()))

    with pytest.raises(IntegrityError):
        pg_session.flush()

    pg_session.rollback()
    bundle, export_run, run, gate, detection_run, readiness = _persist_environment_spec(pg_session)
    spec = _environment_spec(bundle, run, detection_run, readiness)
    pg_session.add(spec)
    pg_session.flush()
    pg_session.add(_environment_issue(spec, environment_spec_id=uuid.uuid4()))

    with pytest.raises(IntegrityError):
        pg_session.flush()
