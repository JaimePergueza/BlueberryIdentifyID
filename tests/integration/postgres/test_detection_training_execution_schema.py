import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from blueberry_microid.infrastructure.db.models import (
    DetectionTrainingExecutionIssueModel,
    DetectionTrainingExecutionRunModel,
)
from tests.integration.postgres.test_detection_training_artifact_schema import (
    _artifact_policy,
    _persist_artifact_policy,
)

pytestmark = pytest.mark.postgres


def _execution_run(bundle, run, detection_run, readiness, environment_spec, artifact_policy, **kwargs):
    values = {
        "detection_training_run_id": detection_run.id,
        "readiness_report_id": readiness.id,
        "environment_spec_id": environment_spec.id,
        "artifact_policy_id": artifact_policy.id,
        "annotation_bundle_run_id": bundle.id,
        "dataset_release_id": run.dataset_release_id,
        "status": "manual_required",
        "decision": "manual_confirmation_required",
        "mode": "scaffold_only",
        "is_executable": False,
        "config": {"mode": "scaffold_only"},
        "prerequisite_summary": {"detection_training_run_status": "planned"},
        "repository_safety_summary": {"is_safe": True},
        "execution_plan": {"manual_steps": []},
        "command_preview": {"command": "yolo detect train ..."},
        "expected_outputs": {"weights_path_planned": "/tmp/blueberry-artifacts/run1/weights/best.pt"},
        "risk_summary": {"error_codes": [], "warning_codes": []},
        "recommendation_summary": {"next_steps": []},
        "error_count": 0,
        "warning_count": 1,
        "info_count": 2,
    }
    values.update(kwargs)
    return DetectionTrainingExecutionRunModel(**values)


def _execution_issue(execution_run, **kwargs):
    values = {
        "execution_run_id": execution_run.id,
        "severity": "info",
        "code": "no_training_executed",
        "message": "no training command was executed by this evaluation",
        "details": None,
    }
    values.update(kwargs)
    return DetectionTrainingExecutionIssueModel(**values)


def _persist_execution_run(pg_session):
    bundle, export_run, run, gate, detection_run, readiness, environment_spec = _persist_artifact_policy(pg_session)
    artifact_policy = _artifact_policy(bundle, run, detection_run, readiness, environment_spec)
    pg_session.add(artifact_policy)
    pg_session.flush()
    return bundle, export_run, run, gate, detection_run, readiness, environment_spec, artifact_policy


def test_alembic_created_detection_training_execution_tables(pg_session):
    rows = (
        pg_session.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN (
                      'detection_training_execution_runs',
                      'detection_training_execution_issues'
                  )
                ORDER BY table_name
                """
            )
        )
        .scalars()
        .all()
    )

    assert rows == ["detection_training_execution_issues", "detection_training_execution_runs"]


def test_status_check_constraint_rejects_unknown_value(pg_session):
    bundle, export_run, run, gate, detection_run, readiness, environment_spec, artifact_policy = (
        _persist_execution_run(pg_session)
    )
    pg_session.add(
        _execution_run(bundle, run, detection_run, readiness, environment_spec, artifact_policy, status="running")
    )

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_decision_check_constraint_rejects_unknown_value(pg_session):
    bundle, export_run, run, gate, detection_run, readiness, environment_spec, artifact_policy = (
        _persist_execution_run(pg_session)
    )
    pg_session.add(
        _execution_run(
            bundle, run, detection_run, readiness, environment_spec, artifact_policy, decision="approved"
        )
    )

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_mode_check_constraint_rejects_unknown_value(pg_session):
    bundle, export_run, run, gate, detection_run, readiness, environment_spec, artifact_policy = (
        _persist_execution_run(pg_session)
    )
    pg_session.add(
        _execution_run(
            bundle, run, detection_run, readiness, environment_spec, artifact_policy, mode="real_training"
        )
    )

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_severity_check_constraint_rejects_unknown_value(pg_session):
    bundle, export_run, run, gate, detection_run, readiness, environment_spec, artifact_policy = (
        _persist_execution_run(pg_session)
    )
    execution_run = _execution_run(bundle, run, detection_run, readiness, environment_spec, artifact_policy)
    pg_session.add(execution_run)
    pg_session.flush()
    pg_session.add(_execution_issue(execution_run, severity="critical"))

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_json_columns_round_trip_as_jsonb(pg_session):
    bundle, export_run, run, gate, detection_run, readiness, environment_spec, artifact_policy = (
        _persist_execution_run(pg_session)
    )
    execution_run = _execution_run(
        bundle,
        run,
        detection_run,
        readiness,
        environment_spec,
        artifact_policy,
        execution_plan={"manual_steps": ["review bundle"], "prohibited_actions": ["do not run in CI"]},
        repository_safety_summary={"is_safe": True, "missing_gitignore_patterns": []},
    )
    pg_session.add(execution_run)
    pg_session.flush()
    pg_session.refresh(execution_run)

    assert execution_run.execution_plan["manual_steps"] == ["review bundle"]
    assert execution_run.repository_safety_summary["is_safe"] is True
    column_type = pg_session.execute(
        text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'detection_training_execution_runs' AND column_name = 'execution_plan'"
        )
    ).scalar_one()
    assert column_type == "jsonb"


def test_foreign_keys_are_enforced_for_execution_run(pg_session):
    bundle, export_run, run, gate, detection_run, readiness, environment_spec, artifact_policy = (
        _persist_execution_run(pg_session)
    )
    pg_session.add(
        _execution_run(
            bundle,
            run,
            detection_run,
            readiness,
            environment_spec,
            artifact_policy,
            detection_training_run_id=uuid.uuid4(),
        )
    )

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_foreign_keys_are_enforced_for_execution_issue(pg_session):
    pg_session.rollback()
    bundle, export_run, run, gate, detection_run, readiness, environment_spec, artifact_policy = (
        _persist_execution_run(pg_session)
    )
    execution_run = _execution_run(bundle, run, detection_run, readiness, environment_spec, artifact_policy)
    pg_session.add(execution_run)
    pg_session.flush()
    pg_session.add(_execution_issue(execution_run, execution_run_id=uuid.uuid4()))

    with pytest.raises(IntegrityError):
        pg_session.flush()
