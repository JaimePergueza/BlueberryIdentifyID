from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from blueberry_microid.infrastructure.config.settings import Settings


def _json_ready(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect local YOLO training metadata without modifying the DB.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--execution-run-id")
    group.add_argument("--local-training-run-id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    raw_id = args.execution_run_id or args.local_training_run_id
    try:
        execution_run_id = UUID(raw_id)
    except ValueError:
        print("inspect_local_yolo_training_run failed: run id must be a valid UUID", file=sys.stderr)
        return 1

    try:
        engine = create_engine(Settings().database_url)
        with engine.connect() as conn:
            run = conn.execute(
                text(
                    """
                    SELECT
                        er.id AS local_training_execution_run_id,
                        er.id AS linked_detection_training_execution_run_id,
                        er.status,
                        er.decision,
                        er.created_at AS started_at,
                        er.completed_at,
                        er.error_count AS issue_count,
                        er.error_message,
                        er.artifact_policy_id
                    FROM detection_training_execution_runs er
                    WHERE er.id = :execution_run_id
                    """
                ),
                {"execution_run_id": execution_run_id},
            ).mappings().first()
            if run is None:
                print(
                    f"inspect_local_yolo_training_run failed: execution_run_id not found: {execution_run_id}",
                    file=sys.stderr,
                )
                return 1
            artifacts = list(
                conn.execute(
                    text(
                        """
                        SELECT
                            artifact_kind,
                            artifact_state,
                            artifact_path,
                            relative_path,
                            file_extension,
                            size_bytes,
                            checksum_sha256 IS NOT NULL AS checksum_present
                        FROM detection_training_artifact_records
                        WHERE artifact_policy_id = :artifact_policy_id
                        ORDER BY artifact_state, artifact_kind, artifact_path
                        """
                    ),
                    {"artifact_policy_id": run["artifact_policy_id"]},
                ).mappings()
            )
    except SQLAlchemyError as exc:
        print(f"inspect_local_yolo_training_run failed: could not read database: {exc}", file=sys.stderr)
        return 1

    artifact_summary: dict[str, int] = {}
    for artifact in artifacts:
        artifact_summary[artifact["artifact_kind"]] = artifact_summary.get(artifact["artifact_kind"], 0) + 1
    payload = {key: _json_ready(value) for key, value in run.items() if key != "artifact_policy_id"}
    payload["artifact_count"] = len(artifacts)
    payload["artifact_summary"] = artifact_summary
    payload["artifacts"] = [{key: _json_ready(value) for key, value in artifact.items()} for artifact in artifacts]
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
