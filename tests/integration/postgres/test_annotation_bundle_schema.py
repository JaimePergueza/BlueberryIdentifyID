import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from blueberry_microid.infrastructure.db.models import AnnotationBundleFileModel, AnnotationBundleRunModel
from tests.integration.postgres.test_petri_annotation_export_schema import _create_export_run_with_review

pytestmark = pytest.mark.postgres


def _bundle_run(export_run, run, **kwargs):
    values = {
        "petri_annotation_export_run_id": export_run.id,
        "dataset_release_id": run.dataset_release_id,
        "petri_segmentation_run_id": run.id,
        "status": "dry_run",
        "is_completed": True,
        "config": {"dry_run": True},
        "output_dir": "/tmp/not-written",
        "dry_run": True,
        "file_count": 1,
        "annotation_count": 1,
        "image_count": 1,
        "label_count": 1,
        "validation_summary": {"is_valid": True, "errors": []},
        "bundle_manifest": {"contains_training": False, "contains_taxonomy": False},
    }
    values.update(kwargs)
    return AnnotationBundleRunModel(**values)


def _bundle_file(bundle_run, **kwargs):
    values = {
        "bundle_run_id": bundle_run.id,
        "file_role": "bundle_manifest",
        "file_path": "/tmp/not-written/manifest.json",
        "relative_path": "manifest.json",
        "content_type": "application/json",
        "size_bytes": 42,
        "checksum_sha256": "a" * 64,
    }
    values.update(kwargs)
    return AnnotationBundleFileModel(**values)


def test_alembic_created_annotation_bundle_tables(pg_session):
    rows = (
        pg_session.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('annotation_bundle_runs', 'annotation_bundle_files')
                ORDER BY table_name
                """
            )
        )
        .scalars()
        .all()
    )

    assert rows == ["annotation_bundle_files", "annotation_bundle_runs"]


def test_bundle_status_and_file_role_constraints(pg_session):
    export_run, _, run, *_ = _create_export_run_with_review(pg_session)
    bundle = _bundle_run(export_run, run, status="training")
    pg_session.add(bundle)

    with pytest.raises(IntegrityError):
        pg_session.flush()

    pg_session.rollback()
    export_run, _, run, *_ = _create_export_run_with_review(pg_session)
    bundle = _bundle_run(export_run, run)
    pg_session.add(bundle)
    pg_session.flush()
    pg_session.add(_bundle_file(bundle, file_role="tensorflow_model"))

    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_bundle_json_columns_round_trip_as_jsonb(pg_session):
    export_run, _, run, *_ = _create_export_run_with_review(pg_session)
    bundle = _bundle_run(
        export_run,
        run,
        validation_summary={"is_valid": True, "split_counts": {"train": 1}},
        bundle_manifest={"contains_training": False, "files": [{"relative_path": "manifest.json"}]},
    )
    pg_session.add(bundle)
    pg_session.flush()
    pg_session.refresh(bundle)

    assert bundle.validation_summary["split_counts"]["train"] == 1
    assert bundle.bundle_manifest["contains_training"] is False
    column_type = pg_session.execute(
        text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'annotation_bundle_runs' AND column_name = 'bundle_manifest'"
        )
    ).scalar_one()
    assert column_type == "jsonb"


def test_bundle_foreign_keys_are_enforced(pg_session):
    export_run, _, run, *_ = _create_export_run_with_review(pg_session)
    bundle = _bundle_run(export_run, run, petri_annotation_export_run_id=uuid.uuid4())
    pg_session.add(bundle)

    with pytest.raises(IntegrityError):
        pg_session.flush()

    pg_session.rollback()
    export_run, _, run, *_ = _create_export_run_with_review(pg_session)
    bundle = _bundle_run(export_run, run)
    pg_session.add(bundle)
    pg_session.flush()
    pg_session.add(_bundle_file(bundle, bundle_run_id=uuid.uuid4()))

    with pytest.raises(IntegrityError):
        pg_session.flush()
