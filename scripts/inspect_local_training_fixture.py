from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from blueberry_microid.infrastructure.config.settings import Settings


def _mask_database_url(url: str) -> str:
    return url.replace("blueberry:blueberry", "blueberry:***")


def _json_ready(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect a persisted local training fixture without modifying it.")
    parser.add_argument("--execution-run-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    database_url = Settings().database_url
    query = text(
        """
        SELECT
            ab.id AS annotation_bundle_run_id,
            ab.status AS annotation_bundle_status,
            aq.id AS annotation_quality_gate_run_id,
            aq.status AS annotation_quality_gate_status,
            dt.id AS detection_training_run_id,
            dt.status AS detection_training_status,
            rr.id AS readiness_report_id,
            rr.status AS readiness_status,
            rr.decision AS readiness_decision,
            es.id AS environment_spec_id,
            es.status AS environment_status,
            es.decision AS environment_decision,
            ap.id AS artifact_policy_id,
            ap.status AS artifact_policy_status,
            ap.decision AS artifact_policy_decision,
            ap.artifact_root_dir AS artifact_root_dir,
            er.id AS execution_run_id,
            er.status AS execution_status,
            er.decision AS execution_decision,
            bf.file_path AS dataset_yaml_path
        FROM detection_training_execution_runs er
        JOIN detection_training_runs dt ON dt.id = er.detection_training_run_id
        JOIN annotation_bundle_runs ab ON ab.id = er.annotation_bundle_run_id
        LEFT JOIN annotation_quality_gate_runs aq ON aq.id = dt.annotation_quality_gate_run_id
        JOIN detection_training_readiness_reports rr ON rr.id = er.readiness_report_id
        JOIN detection_training_environment_specs es ON es.id = er.environment_spec_id
        JOIN detection_training_artifact_policies ap ON ap.id = er.artifact_policy_id
        LEFT JOIN annotation_bundle_files bf
            ON bf.bundle_run_id = ab.id AND bf.file_role = 'dataset_yaml'
        WHERE er.id = :execution_run_id
        """
    )
    try:
        execution_run_id = UUID(args.execution_run_id)
    except ValueError:
        print("inspect_local_training_fixture failed: --execution-run-id must be a valid UUID", file=sys.stderr)
        return 1

    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            row = conn.execute(query, {"execution_run_id": execution_run_id}).mappings().first()
    except SQLAlchemyError as exc:
        print(
            "inspect_local_training_fixture failed: could not connect to database "
            f"{_mask_database_url(database_url)}: {exc}",
            file=sys.stderr,
        )
        return 1

    if row is None:
        print(
            f"inspect_local_training_fixture failed: execution_run_id not found: {execution_run_id}",
            file=sys.stderr,
        )
        return 1

    print(json.dumps({key: _json_ready(value) for key, value in row.items()}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
