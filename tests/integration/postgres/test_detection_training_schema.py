import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from blueberry_microid.infrastructure.db.models import (
    DetectionTrainingIssueModel,
    DetectionTrainingRunModel,
)
from tests.integration.postgres.test_annotation_quality_gate_schema import _gate_run, _persist_bundle

pytestmark = pytest.mark.postgres


def _detection_run(bundle, export_run, run, gate, **kwargs):
    values = {
        "annotation_bundle_run_id": bundle.id,
        "annotation_quality_gate_run_id": gate.id,
        "dataset_release_id": run.dataset_release_id,
        "petri_annotation_export_run_id": export_run.id,
        "algorithm": "yolo_dry_run",
        "mode": "dry_run",
        "status": "planned",
        "is_runnable": True,
        "config": {"algorithm": "yolo_dry_run"},
        "training_plan": {"algorithm": "yolo_dry_run"},
        "command_preview": {"dry_run_only": True, "command": "yolo detect train data=dataset.yaml"},
        "dataset_summary": {"dataset_yaml_present": True},
        "quality_gate_summary": {"status": "passed"},
        "expected_outputs": {"weights_path_planned": "runs/weights/best.pt"},
        "issue_count": 1,
        "warning_count": 0,
        "error_count": 0,
    }
    values.update(kwargs)
    return DetectionTrainingRunModel(**values)


def _detection_issue(run, **kwargs):
    values = {
        "detection_training_run_id": run.id,
        "severity": "info",
        "code": "no_training_executed",
        "message": "this run only planned a dry-run; no training was executed",
        "details": None,
    }
    values.update(kwargs)
    return DetectionTrainingIssueModel(**values)


def _persist_gate(pg_session):
    bundle, export_run, run = _persist_bundle(pg_session)
    gate = _gate_run(bundle, export_run, run)
    pg_session.add(gate)
    pg_session.flush()
    return bundle, export_run, run, gate


def test_alembic_created_detection_training_tables(pg_session):
    rows = (
        pg_session.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('detection_training_runs', 'detection_training_issues')
                ORDER BY table_name
                """
            )
        )
        .scalars()
        .all()
    )

    assert rows == ["detection_training_issues", "detection_training_runs"]


def test_algorithm_check_constraint_rejects_unknown_value(pg_session):
    bundle, export_run, run, gate = _persist_gate(pg_session)
    pg_session.add(_detection_run(bundle, export_run, run, gate, algorithm="yolo_train"))

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_mode_check_constraint_rejects_unknown_value(pg_session):
    bundle, export_run, run, gate = _persist_gate(pg_session)
    pg_session.add(_detection_run(bundle, export_run, run, gate, mode="real_run"))

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_status_check_constraint_rejects_unknown_value(pg_session):
    bundle, export_run, run, gate = _persist_gate(pg_session)
    pg_session.add(_detection_run(bundle, export_run, run, gate, status="training"))

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_severity_check_constraint_rejects_unknown_value(pg_session):
    bundle, export_run, run, gate = _persist_gate(pg_session)
    detection_run = _detection_run(bundle, export_run, run, gate)
    pg_session.add(detection_run)
    pg_session.flush()
    pg_session.add(_detection_issue(detection_run, severity="critical"))

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_json_columns_round_trip_as_jsonb(pg_session):
    bundle, export_run, run, gate = _persist_gate(pg_session)
    detection_run = _detection_run(
        bundle,
        export_run,
        run,
        gate,
        training_plan={"algorithm": "yolo_dry_run", "epochs": 50},
        command_preview={"tool": "ultralytics_yolo", "dry_run_only": True},
    )
    pg_session.add(detection_run)
    pg_session.flush()
    pg_session.refresh(detection_run)

    assert detection_run.training_plan["epochs"] == 50
    assert detection_run.command_preview["dry_run_only"] is True
    column_type = pg_session.execute(
        text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'detection_training_runs' AND column_name = 'training_plan'"
        )
    ).scalar_one()
    assert column_type == "jsonb"


def test_foreign_keys_are_enforced(pg_session):
    bundle, export_run, run, gate = _persist_gate(pg_session)
    pg_session.add(_detection_run(bundle, export_run, run, gate, annotation_bundle_run_id=uuid.uuid4()))

    with pytest.raises(IntegrityError):
        pg_session.flush()

    pg_session.rollback()
    bundle, export_run, run, gate = _persist_gate(pg_session)
    detection_run = _detection_run(bundle, export_run, run, gate)
    pg_session.add(detection_run)
    pg_session.flush()
    pg_session.add(_detection_issue(detection_run, detection_training_run_id=uuid.uuid4()))

    with pytest.raises(IntegrityError):
        pg_session.flush()
