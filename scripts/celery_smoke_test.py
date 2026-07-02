#!/usr/bin/env python
"""Operational smoke test for real Redis + Celery async processing.

Run the backing services, API, and worker first:
    docker compose up -d postgres redis
    alembic upgrade head
    uvicorn blueberry_microid.interfaces.api.app:create_app --factory --reload
    celery -A blueberry_microid.infrastructure.tasks.celery_app.celery_app worker --loglevel=info -Q analysis

Then run:
    python scripts/celery_smoke_test.py

The script drives the real asynchronous path: it calls /process-async,
polls /tasks/{task_id}, and then checks AnalysisRun/Prediction/HumanReview.
It uses tiny in-memory Pillow images only; no datasets, no real AI, no
PyTorch, and no taxonomic identification.
"""

from __future__ import annotations

import argparse
import sys
import time
import uuid
from io import BytesIO
from typing import Any

import httpx
from PIL import Image

from blueberry_microid.infrastructure.config.settings import Settings


class SmokeTestFailure(RuntimeError):
    """Raised when the operational smoke flow does not meet expectations."""


def _make_image_bytes(fmt: str, color: str) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (64, 48), color=color).save(buffer, format=fmt)
    return buffer.getvalue()


def _step(message: str) -> None:
    print(f"-> {message}")


def _check(response: httpx.Response, expected_status: int, step: str) -> dict[str, Any]:
    if response.status_code != expected_status:
        raise SmokeTestFailure(
            f"{step}: expected HTTP {expected_status}, got {response.status_code}: {response.text}"
        )
    print(f"   OK ({response.status_code})")
    return response.json() if response.content else {}


def _poll_task_success(client: httpx.Client, task_id: str, timeout_seconds: float, interval_seconds: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_body: dict[str, Any] | None = None

    while time.monotonic() < deadline:
        body = _check(client.get(f"/api/v1/tasks/{task_id}"), 200, f"get task status {task_id}")
        last_body = body
        state = body.get("state")
        print(f"   task state: {state}")
        if state == "SUCCESS":
            return body
        if state == "FAILURE":
            raise SmokeTestFailure(f"task {task_id} failed: {body.get('result')}")
        time.sleep(interval_seconds)

    raise SmokeTestFailure(f"task {task_id} did not reach SUCCESS within {timeout_seconds}s; last={last_body!r}")


def run(base_url: str, *, timeout_seconds: float, interval_seconds: float) -> None:
    unique_suffix = uuid.uuid4().hex[:8]
    with httpx.Client(base_url=base_url, timeout=10.0) as client:
        _step("GET /health")
        body = _check(client.get("/health"), 200, "health check")
        if body.get("status") != "ok":
            raise SmokeTestFailure(f"health check: unexpected body {body!r}")

        _step("POST /api/v1/samples")
        sample = _check(
            client.post("/api/v1/samples", json={"sample_code": f"CELERY-SMOKE-{unique_suffix}"}),
            201,
            "create sample",
        )
        sample_id = sample["id"]

        _step("POST /api/v1/model-versions")
        model_version = _check(
            client.post(
                "/api/v1/model-versions",
                json={"name": f"celery-smoke-engine-{unique_suffix}", "version": "0.1.0", "model_type": "mock"},
            ),
            201,
            "create model version",
        )
        model_version_id = model_version["id"]

        _step("POST /api/v1/samples/{sample_id}/petri-images")
        petri_image = _check(
            client.post(
                f"/api/v1/samples/{sample_id}/petri-images",
                files={"file": ("petri.jpg", _make_image_bytes("JPEG", "white"), "image/jpeg")},
                data={"culture_medium": "PDA"},
            ),
            201,
            "upload petri image",
        )
        petri_image_id = petri_image["id"]

        _step("POST /api/v1/samples/{sample_id}/micro-images")
        micro_image = _check(
            client.post(
                f"/api/v1/samples/{sample_id}/micro-images",
                files={"file": ("micro.png", _make_image_bytes("PNG", "gray"), "image/png")},
                data={"magnification": "400x"},
            ),
            201,
            "upload micro image",
        )
        micro_image_id = micro_image["id"]

        _step("POST /api/v1/analysis-runs")
        analysis_run = _check(
            client.post(
                "/api/v1/analysis-runs",
                json={
                    "sample_id": sample_id,
                    "petri_image_id": petri_image_id,
                    "micro_image_id": micro_image_id,
                    "model_version_id": model_version_id,
                },
            ),
            201,
            "create analysis run",
        )
        analysis_run_id = analysis_run["id"]
        if analysis_run["status"] != "pending":
            raise SmokeTestFailure(f"analysis run: expected pending, got {analysis_run['status']!r}")

        _step("POST /api/v1/analysis-runs/{analysis_run_id}/process-async")
        queued = _check(
            client.post(f"/api/v1/analysis-runs/{analysis_run_id}/process-async"),
            202,
            "queue async processing",
        )
        task_id = queued["task_id"]
        if queued["status"] != "queued":
            raise SmokeTestFailure(f"queue async processing: expected queued, got {queued['status']!r}")

        _step("GET /api/v1/tasks/{task_id} until SUCCESS")
        task_status = _poll_task_success(client, task_id, timeout_seconds, interval_seconds)
        task_result = task_status.get("result") or {}
        if task_result.get("analysis_run_id") not in (None, analysis_run_id):
            raise SmokeTestFailure(f"task result references unexpected analysis_run_id: {task_result!r}")

        _step("GET /api/v1/analysis-runs/{analysis_run_id}")
        final_run = _check(client.get(f"/api/v1/analysis-runs/{analysis_run_id}"), 200, "get final analysis run")
        if final_run["status"] == "pending":
            raise SmokeTestFailure("analysis run remained pending after task SUCCESS")
        if final_run["status"] not in {"completed", "needs_review", "failed"}:
            raise SmokeTestFailure(f"analysis run final status is unexpected: {final_run['status']!r}")
        if final_run["status"] == "failed":
            raise SmokeTestFailure(f"analysis run failed during smoke: {final_run.get('error_message')!r}")

        _step("GET /api/v1/analysis-runs/{analysis_run_id}/prediction")
        prediction = _check(
            client.get(f"/api/v1/analysis-runs/{analysis_run_id}/prediction"),
            200,
            "get prediction",
        )
        if prediction["analysis_run_id"] != analysis_run_id:
            raise SmokeTestFailure("prediction belongs to a different AnalysisRun")

        _step("POST /api/v1/analysis-runs/{analysis_run_id}/reviews")
        review = _check(
            client.post(
                f"/api/v1/analysis-runs/{analysis_run_id}/reviews",
                json={
                    "reviewer_name": "Celery Smoke Reviewer",
                    "review_decision": "confirmed",
                    "comments": "Operational smoke confirmed the async mock pipeline.",
                },
            ),
            201,
            "create final human review",
        )
        if review["is_final"] is not True:
            raise SmokeTestFailure("created human review is not final")

        _step("GET /api/v1/analysis-runs/{analysis_run_id}/reviews/final")
        final_review = _check(
            client.get(f"/api/v1/analysis-runs/{analysis_run_id}/reviews/final"),
            200,
            "get final human review",
        )
        if final_review["id"] != review["id"]:
            raise SmokeTestFailure("final review id does not match the one just created")

    print()
    print(f"SUCCESS: real Celery/Redis smoke passed against {base_url}.")
    print(f"AnalysisRun: {analysis_run_id}")
    print(f"Task: {task_id}")
    print(f"Predicted label (simulated, non-diagnostic): {prediction['predicted_label']}")
    print("Reminder: this used MockInferenceEngine only; no real image analysis, species, or genus identification.")


def main() -> None:
    settings = Settings()
    parser = argparse.ArgumentParser(description="Run the real Celery/Redis operational smoke test.")
    parser.add_argument("base_url", nargs="?", default=settings.api_base_url)
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--interval-seconds", type=float, default=1.0)
    args = parser.parse_args()

    try:
        run(args.base_url, timeout_seconds=args.timeout_seconds, interval_seconds=args.interval_seconds)
    except SmokeTestFailure as exc:
        print(f"FAILED: {exc}")
        sys.exit(1)
    except httpx.ConnectError as exc:
        print(f"FAILED: could not connect to {args.base_url}: {exc}")
        print("Start the API first:")
        print("  uvicorn blueberry_microid.interfaces.api.app:create_app --factory --reload")
        sys.exit(1)


if __name__ == "__main__":
    main()
