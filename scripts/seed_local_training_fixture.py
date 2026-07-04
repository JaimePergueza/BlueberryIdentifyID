from __future__ import annotations

import argparse
import json
import socket
import sys
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from sqlalchemy.engine.url import make_url

from blueberry_microid.infrastructure.config.settings import Settings
from blueberry_microid.infrastructure.db.session.engine import create_db_engine
from blueberry_microid.infrastructure.db.session.session_factory import create_session_factory
from blueberry_microid.interfaces.api.app import create_app

REPO_ROOT = Path(__file__).resolve().parents[1]
EXECUTION_CONFIRMATION = "I understand this will only create a scaffold and will not train a model"
RUNNER_CONFIRMATION = "I confirm local YOLO training outside CI"

SUMMARY_KEYS = (
    "sample_id",
    "analysis_run_id",
    "human_review_id",
    "dataset_snapshot_id",
    "dataset_release_id",
    "image_audit_run_id",
    "petri_segmentation_run_id",
    "petri_region_review_id",
    "petri_annotation_export_run_id",
    "annotation_bundle_run_id",
    "annotation_quality_gate_run_id",
    "detection_training_run_id",
    "readiness_report_id",
    "environment_spec_id",
    "artifact_policy_id",
    "execution_run_id",
    "dataset_yaml_path",
    "artifact_root_dir",
)


class LocalTrainingFixtureError(RuntimeError):
    pass


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _empty_summary() -> dict[str, Any]:
    return {key: None for key in SUMMARY_KEYS}


def _json(summary: dict[str, Any]) -> str:
    return json.dumps(summary, indent=2, sort_keys=True)


def _petri_png() -> bytes:
    image = Image.new("RGB", (160, 160), "white")
    draw = ImageDraw.Draw(image)
    draw.ellipse((48, 48, 82, 82), fill=(25, 25, 25))
    draw.ellipse((92, 64, 124, 96), fill=(45, 45, 45))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _micro_png() -> bytes:
    image = Image.new("RGB", (96, 96), (230, 230, 235))
    draw = ImageDraw.Draw(image)
    for offset in range(12, 84, 18):
        draw.line((0, offset, 96, offset + 12), fill=(120, 120, 130), width=1)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _assert_external_path(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if _is_inside(resolved, REPO_ROOT):
        raise LocalTrainingFixtureError(f"{label} must be outside the repository: {resolved}")
    return resolved


def _run_migrations(database_url: str) -> None:
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(cfg, "head")


def _assert_database_reachable(database_url: str) -> None:
    url = make_url(database_url)
    if not url.drivername.startswith("postgresql"):
        return
    host = url.host or "localhost"
    port = url.port or 5432
    try:
        with socket.create_connection((host, port), timeout=3):
            return
    except OSError as exc:
        raise LocalTrainingFixtureError(
            f"PostgreSQL is not reachable at {host}:{port}; start the local database before seeding"
        ) from exc


def _client(database_url: str, storage_root: Path) -> TestClient:
    app = create_app()
    engine = create_db_engine(database_url)
    app.state.settings = Settings(_env_file=None, database_url=database_url, storage_root=storage_root)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    return TestClient(app, raise_server_exceptions=False)


def _post(client: TestClient, path: str, *, json_body: dict | None = None, files: dict | None = None) -> dict:
    response = client.post(path, json=json_body, files=files)
    if response.status_code not in {200, 201}:
        raise LocalTrainingFixtureError(f"POST {path} failed: {response.status_code} {response.text}")
    return response.json()


def _get(client: TestClient, path: str) -> dict:
    response = client.get(path)
    if response.status_code != 200:
        raise LocalTrainingFixtureError(f"GET {path} failed: {response.status_code} {response.text}")
    return response.json()


def _create_seed(client: TestClient, *, artifact_root: Path, storage_root: Path, dataset_name: str, created_by: str) -> dict:
    summary = _empty_summary()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    prefix = f"{dataset_name}-{stamp}"
    bundle_dir = artifact_root / "bundle" / prefix
    bundle_dir.mkdir(parents=True, exist_ok=True)
    storage_root.mkdir(parents=True, exist_ok=True)

    sample = _post(client, "/api/v1/samples", json_body={"sample_code": f"{prefix}-sample"})
    summary["sample_id"] = sample["id"]

    model = _post(
        client,
        "/api/v1/model-versions",
        json_body={"name": f"{prefix}-mock", "version": "0.1.0", "model_type": "mock"},
    )
    petri = _post(
        client,
        f"/api/v1/samples/{sample['id']}/petri-images",
        files={"file": ("petri_fixture.png", _petri_png(), "image/png")},
    )
    micro = _post(
        client,
        f"/api/v1/samples/{sample['id']}/micro-images",
        files={"file": ("micro_fixture.png", _micro_png(), "image/png")},
    )
    analysis = _post(
        client,
        "/api/v1/analysis-runs",
        json_body={
            "sample_id": sample["id"],
            "petri_image_id": petri["id"],
            "micro_image_id": micro["id"],
            "model_version_id": model["id"],
        },
    )
    summary["analysis_run_id"] = analysis["id"]
    _post(client, f"/api/v1/analysis-runs/{analysis['id']}/process")
    review = _post(
        client,
        f"/api/v1/analysis-runs/{analysis['id']}/reviews",
        json_body={"reviewer_name": created_by, "review_decision": "confirmed"},
    )
    summary["human_review_id"] = review["id"]

    snapshot = _post(
        client,
        "/api/v1/datasets/snapshots",
        json_body={
            "name": f"{dataset_name}-snapshot",
            "version": stamp,
            "created_by": created_by,
            "notes": "Synthetic technical fixture for local YOLO smoke testing; not scientific data.",
        },
    )
    summary["dataset_snapshot_id"] = snapshot["id"]
    release = _post(
        client,
        "/api/v1/datasets/releases",
        json_body={
            "dataset_snapshot_id": snapshot["id"],
            "name": f"{dataset_name}-release",
            "version": stamp,
            "created_by": created_by,
        },
    )
    summary["dataset_release_id"] = release["id"]
    audit = _post(client, "/api/v1/ml/image-audits", json_body={"dataset_release_id": release["id"]})
    summary["image_audit_run_id"] = audit["id"]
    segmentation = _post(
        client,
        "/api/v1/ml/petri-segmentations",
        json_body={"dataset_release_id": release["id"], "image_audit_run_id": audit["id"]},
    )
    summary["petri_segmentation_run_id"] = segmentation["id"]
    if not segmentation.get("regions"):
        raise LocalTrainingFixtureError("Petri fixture produced no candidate regions")
    region_id = segmentation["regions"][0]["id"]
    region_review = _post(
        client,
        f"/api/v1/ml/petri-regions/{region_id}/reviews",
        json_body={"decision": "candidate_valid", "reviewer_name": created_by, "confidence_score": 0.9},
    )
    summary["petri_region_review_id"] = region_review["id"]
    export = _post(
        client,
        "/api/v1/ml/petri-annotation-exports",
        json_body={
            "dataset_release_id": release["id"],
            "petri_segmentation_run_id": segmentation["id"],
            "config": {"export_format": "blueberry_manifest"},
            "created_by": created_by,
        },
    )
    summary["petri_annotation_export_run_id"] = export["id"]
    bundle = _post(
        client,
        "/api/v1/ml/annotation-bundles",
        json_body={
            "petri_annotation_export_run_id": export["id"],
            "config": {"dry_run": False, "output_dir": str(bundle_dir), "copy_images": False},
            "created_by": created_by,
        },
    )
    summary["annotation_bundle_run_id"] = bundle["id"]
    files = _get(client, f"/api/v1/ml/annotation-bundles/{bundle['id']}/files")["files"]
    dataset_yaml = next((Path(item["file_path"]) for item in files if item["relative_path"] == "dataset.yaml"), None)
    if dataset_yaml is None or not dataset_yaml.exists():
        raise LocalTrainingFixtureError("annotation bundle did not produce dataset.yaml")
    summary["dataset_yaml_path"] = str(dataset_yaml)

    gate = _post(
        client,
        "/api/v1/ml/annotation-quality-gates",
        json_body={
            "annotation_bundle_run_id": bundle["id"],
            "config": {"fail_on_empty_split": False, "warn_on_single_class": False},
            "created_by": created_by,
        },
    )
    summary["annotation_quality_gate_run_id"] = gate["id"]
    if gate["status"] != "passed":
        raise LocalTrainingFixtureError(f"annotation quality gate did not pass: {gate}")

    training = _post(
        client,
        "/api/v1/ml/detection-training-runs",
        json_body={
            "annotation_bundle_run_id": bundle["id"],
            "annotation_quality_gate_run_id": gate["id"],
            "created_by": created_by,
        },
    )
    summary["detection_training_run_id"] = training["id"]
    if training["status"] != "planned":
        raise LocalTrainingFixtureError(f"detection training run is not planned: {training}")

    readiness = _post(
        client,
        "/api/v1/ml/detection-training-readiness-reports",
        json_body={"detection_training_run_id": training["id"], "config": {"require_minimum_data": False}},
    )
    summary["readiness_report_id"] = readiness["id"]
    if not readiness["is_ready"]:
        raise LocalTrainingFixtureError(f"readiness report is not ready: {readiness}")

    environment = _post(
        client,
        "/api/v1/ml/detection-training-environment-specs",
        json_body={
            "detection_training_run_id": training["id"],
            "readiness_report_id": readiness["id"],
            "config": {
                "allow_cpu_training": False,
                "require_gpu": False,
                "require_cuda": False,
                "require_ultralytics": False,
                "require_torch": False,
                "artifact_output_dir": str(artifact_root),
                "pretrained_weights_policy": "not_applicable",
                "allow_ci_training": False,
                "allow_artifacts_inside_repo": False,
            },
        },
    )
    summary["environment_spec_id"] = environment["id"]
    if not environment["is_environment_ready"]:
        raise LocalTrainingFixtureError(f"environment spec is not ready: {environment}")

    policy = _post(
        client,
        "/api/v1/ml/detection-training-artifact-policies",
        json_body={
            "detection_training_run_id": training["id"],
            "readiness_report_id": readiness["id"],
            "environment_spec_id": environment["id"],
            "config": {
                "artifact_root_dir": str(artifact_root),
                "allow_artifacts_inside_repo": False,
                "allow_actual_artifact_registration": True,
                "register_planned_artifacts": True,
                "register_actual_artifacts": True,
                "require_gitignore_rules": True,
            },
        },
    )
    summary["artifact_policy_id"] = policy["id"]
    if not policy["is_policy_ready"]:
        raise LocalTrainingFixtureError(f"artifact policy is not ready: {policy}")

    execution = _post(
        client,
        "/api/v1/ml/detection-training-execution-runs",
        json_body={
            "detection_training_run_id": training["id"],
            "readiness_report_id": readiness["id"],
            "environment_spec_id": environment["id"],
            "artifact_policy_id": policy["id"],
            "config": {
                "manual_confirmation_text": EXECUTION_CONFIRMATION,
                "allow_ready_to_execute_status": True,
                "enable_real_training": False,
                "dry_run_only": True,
                "block_in_ci": True,
            },
            "created_by": created_by,
        },
    )
    summary["execution_run_id"] = execution["id"]
    if execution["status"] != "ready_to_execute":
        raise LocalTrainingFixtureError(f"execution run is not ready_to_execute: {execution}")
    summary["artifact_root_dir"] = str(artifact_root)
    summary["dry_run_validation_command"] = (
        "python scripts/run_local_yolo_training.py "
        f"--execution-run-id {execution['id']} "
        f"--artifact-root-dir {artifact_root} "
        "--base-model-path <external-local-base-model-path> "
        f"--manual-confirmation-text \"{RUNNER_CONFIRMATION}\" "
        "--dry-run-validation-only"
    )
    summary["fixture_kind"] = "synthetic_technical_smoke_fixture"
    summary["scientific_claim"] = "none"
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed a local synthetic end-to-end YOLO training fixture.")
    parser.add_argument("--artifact-root-dir", required=True)
    parser.add_argument("--storage-root-dir", required=True)
    parser.add_argument("--created-by", default="local-fixture-operator")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--emit-json", action="store_true")
    parser.add_argument("--base-model-path")
    parser.add_argument("--dataset-name", default="fase33-local-yolo-smoke")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    artifact_root = _assert_external_path(Path(args.artifact_root_dir), "artifact_root_dir")
    storage_root = _assert_external_path(Path(args.storage_root_dir), "storage_root_dir")
    summary = _empty_summary()
    summary.update(
        {
            "artifact_root_dir": str(artifact_root),
            "storage_root_dir": str(storage_root),
            "dataset_name": args.dataset_name,
            "dry_run": args.dry_run,
            "force": args.force,
            "fixture_kind": "synthetic_technical_smoke_fixture",
            "scientific_claim": "none",
        }
    )
    if args.base_model_path:
        summary["base_model_path"] = str(_assert_external_path(Path(args.base_model_path), "base_model_path"))

    if args.dry_run:
        summary["would_persist"] = False
        summary["would_train"] = False
        print(_json(summary) if args.emit_json else f"Dry run OK\n{_json(summary)}")
        return 0

    database_url = Settings().database_url
    summary["database_url"] = database_url
    _assert_database_reachable(database_url)
    _run_migrations(database_url)
    client = _client(database_url, storage_root)
    with client:
        summary.update(
            _create_seed(
                client,
                artifact_root=artifact_root,
                storage_root=storage_root,
                dataset_name=args.dataset_name,
                created_by=args.created_by,
            )
        )
    print(_json(summary) if args.emit_json else f"Seed completed\n{_json(summary)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except LocalTrainingFixtureError as exc:
        print(f"seed_local_training_fixture failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
