import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from blueberry_microid.infrastructure.db.models import (
    DetectionTrainingArtifactIssueModel,
    DetectionTrainingArtifactPolicyModel,
    DetectionTrainingArtifactRecordModel,
)
from tests.integration.postgres.test_detection_training_environment_schema import _persist_environment_spec

pytestmark = pytest.mark.postgres


def _artifact_policy(bundle, run, detection_run, readiness, environment_spec, **kwargs):
    values = {
        "detection_training_run_id": detection_run.id,
        "readiness_report_id": readiness.id,
        "environment_spec_id": environment_spec.id,
        "annotation_bundle_run_id": bundle.id,
        "dataset_release_id": run.dataset_release_id,
        "decision": "artifact_policy_ready",
        "status": "ready",
        "is_policy_ready": True,
        "config": {"artifact_root_dir": "/tmp/blueberry-artifacts"},
        "artifact_root_dir": "/tmp/blueberry-artifacts",
        "planned_output_summary": {"weights_path_planned": "/tmp/blueberry-artifacts/run1/weights/best.pt"},
        "storage_policy": {"artifact_root_dir": "/tmp/blueberry-artifacts"},
        "git_policy": {"gitignore_modified": False},
        "checksum_policy": {"checksums_computed": False},
        "registry_summary": {"planned_record_count": 1, "actual_record_count": 0},
        "risk_summary": {"error_codes": [], "warning_codes": []},
        "recommendation_summary": {"next_steps": []},
        "error_count": 0,
        "warning_count": 0,
        "info_count": 1,
    }
    values.update(kwargs)
    return DetectionTrainingArtifactPolicyModel(**values)


def _artifact_record(policy, detection_run, **kwargs):
    values = {
        "artifact_policy_id": policy.id,
        "detection_training_run_id": detection_run.id,
        "artifact_kind": "planned_weights",
        "artifact_state": "planned",
        "location_type": "local_path",
        "artifact_path": "/tmp/blueberry-artifacts/run1/weights/best.pt",
        "relative_path": None,
        "external_uri": None,
        "file_extension": ".pt",
        "size_bytes": None,
        "checksum_sha256": None,
        "artifact_metadata": None,
    }
    values.update(kwargs)
    return DetectionTrainingArtifactRecordModel(**values)


def _artifact_issue(policy, **kwargs):
    values = {
        "artifact_policy_id": policy.id,
        "severity": "info",
        "code": "no_training_executed",
        "message": "no training was executed by this evaluation",
        "artifact_path": None,
        "details": None,
    }
    values.update(kwargs)
    return DetectionTrainingArtifactIssueModel(**values)


def _persist_artifact_policy(pg_session):
    bundle, export_run, run, gate, detection_run, readiness = _persist_environment_spec(pg_session)
    from tests.integration.postgres.test_detection_training_environment_schema import _environment_spec

    environment_spec = _environment_spec(bundle, run, detection_run, readiness)
    pg_session.add(environment_spec)
    pg_session.flush()
    return bundle, export_run, run, gate, detection_run, readiness, environment_spec


def test_alembic_created_detection_training_artifact_tables(pg_session):
    rows = (
        pg_session.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN (
                      'detection_training_artifact_policies',
                      'detection_training_artifact_records',
                      'detection_training_artifact_issues'
                  )
                ORDER BY table_name
                """
            )
        )
        .scalars()
        .all()
    )

    assert rows == [
        "detection_training_artifact_issues",
        "detection_training_artifact_policies",
        "detection_training_artifact_records",
    ]


def test_decision_check_constraint_rejects_unknown_value(pg_session):
    bundle, export_run, run, gate, detection_run, readiness, environment_spec = _persist_artifact_policy(pg_session)
    pg_session.add(
        _artifact_policy(bundle, run, detection_run, readiness, environment_spec, decision="ready_to_ship")
    )

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_status_check_constraint_rejects_unknown_value(pg_session):
    bundle, export_run, run, gate, detection_run, readiness, environment_spec = _persist_artifact_policy(pg_session)
    pg_session.add(_artifact_policy(bundle, run, detection_run, readiness, environment_spec, status="in_progress"))

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_artifact_kind_check_constraint_rejects_unknown_value(pg_session):
    bundle, export_run, run, gate, detection_run, readiness, environment_spec = _persist_artifact_policy(pg_session)
    policy = _artifact_policy(bundle, run, detection_run, readiness, environment_spec)
    pg_session.add(policy)
    pg_session.flush()
    pg_session.add(_artifact_record(policy, detection_run, artifact_kind="actual_species_labels"))

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_artifact_state_check_constraint_rejects_unknown_value(pg_session):
    bundle, export_run, run, gate, detection_run, readiness, environment_spec = _persist_artifact_policy(pg_session)
    policy = _artifact_policy(bundle, run, detection_run, readiness, environment_spec)
    pg_session.add(policy)
    pg_session.flush()
    pg_session.add(_artifact_record(policy, detection_run, artifact_state="uploaded"))

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_location_type_check_constraint_rejects_unknown_value(pg_session):
    bundle, export_run, run, gate, detection_run, readiness, environment_spec = _persist_artifact_policy(pg_session)
    policy = _artifact_policy(bundle, run, detection_run, readiness, environment_spec)
    pg_session.add(policy)
    pg_session.flush()
    pg_session.add(_artifact_record(policy, detection_run, location_type="s3_bucket"))

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_severity_check_constraint_rejects_unknown_value(pg_session):
    bundle, export_run, run, gate, detection_run, readiness, environment_spec = _persist_artifact_policy(pg_session)
    policy = _artifact_policy(bundle, run, detection_run, readiness, environment_spec)
    pg_session.add(policy)
    pg_session.flush()
    pg_session.add(_artifact_issue(policy, severity="critical"))

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_json_columns_round_trip_as_jsonb(pg_session):
    bundle, export_run, run, gate, detection_run, readiness, environment_spec = _persist_artifact_policy(pg_session)
    policy = _artifact_policy(
        bundle,
        run,
        detection_run,
        readiness,
        environment_spec,
        storage_policy={"artifact_root_dir": "/tmp/blueberry-artifacts", "allow_artifacts_outside_repo": True},
        registry_summary={"planned_record_count": 4, "actual_record_count": 0},
    )
    pg_session.add(policy)
    pg_session.flush()
    pg_session.refresh(policy)

    assert policy.storage_policy["allow_artifacts_outside_repo"] is True
    assert policy.registry_summary["planned_record_count"] == 4
    column_type = pg_session.execute(
        text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'detection_training_artifact_policies' AND column_name = 'storage_policy'"
        )
    ).scalar_one()
    assert column_type == "jsonb"


def test_artifact_metadata_column_round_trips_as_jsonb(pg_session):
    bundle, export_run, run, gate, detection_run, readiness, environment_spec = _persist_artifact_policy(pg_session)
    policy = _artifact_policy(bundle, run, detection_run, readiness, environment_spec)
    pg_session.add(policy)
    pg_session.flush()
    record = _artifact_record(policy, detection_run, artifact_metadata={"note": "planned only"})
    pg_session.add(record)
    pg_session.flush()
    pg_session.refresh(record)

    assert record.artifact_metadata["note"] == "planned only"
    column_type = pg_session.execute(
        text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'detection_training_artifact_records' AND column_name = 'artifact_metadata'"
        )
    ).scalar_one()
    assert column_type == "jsonb"


def test_foreign_keys_are_enforced_for_policy(pg_session):
    bundle, export_run, run, gate, detection_run, readiness, environment_spec = _persist_artifact_policy(pg_session)
    pg_session.add(
        _artifact_policy(
            bundle, run, detection_run, readiness, environment_spec, detection_training_run_id=uuid.uuid4()
        )
    )

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_foreign_keys_are_enforced_for_record_and_issue(pg_session):
    pg_session.rollback()
    bundle, export_run, run, gate, detection_run, readiness, environment_spec = _persist_artifact_policy(pg_session)
    policy = _artifact_policy(bundle, run, detection_run, readiness, environment_spec)
    pg_session.add(policy)
    pg_session.flush()

    pg_session.add(_artifact_record(policy, detection_run, artifact_policy_id=uuid.uuid4()))
    with pytest.raises(IntegrityError):
        pg_session.flush()

    pg_session.rollback()
    bundle, export_run, run, gate, detection_run, readiness, environment_spec = _persist_artifact_policy(pg_session)
    policy = _artifact_policy(bundle, run, detection_run, readiness, environment_spec)
    pg_session.add(policy)
    pg_session.flush()
    pg_session.add(_artifact_issue(policy, artifact_policy_id=uuid.uuid4()))

    with pytest.raises(IntegrityError):
        pg_session.flush()
