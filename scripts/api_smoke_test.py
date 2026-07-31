#!/usr/bin/env python
"""Authenticated operational smoke test for a running BlueberryMicroID API.

Create an administrator first with `python scripts/create_admin.py`, then set
BLUEBERRY_ADMIN_USERNAME and BLUEBERRY_ADMIN_PASSWORD before running this
script. It exercises the legacy synchronous mock-processing path only.
"""

from __future__ import annotations

import os
import sys
import uuid
from io import BytesIO

import httpx
from PIL import Image

DEFAULT_BASE_URL = "http://127.0.0.1:8000"


class SmokeTestFailure(RuntimeError):
    """Raised when a step gets a response other than the one expected."""


def _make_image_bytes(fmt: str, color: str) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (64, 48), color=color).save(buffer, format=fmt)
    return buffer.getvalue()


def _step(description: str) -> None:
    print(f"-> {description}")


def _check(response: httpx.Response, expected_status: int, step: str) -> dict:
    if response.status_code != expected_status:
        raise SmokeTestFailure(
            f"{step}: expected HTTP {expected_status}, got {response.status_code}: {response.text}"
        )
    print(f"   OK ({response.status_code})")
    return response.json() if response.content else {}


def run(base_url: str) -> None:
    username = os.getenv("BLUEBERRY_ADMIN_USERNAME")
    password = os.getenv("BLUEBERRY_ADMIN_PASSWORD")
    if not username or not password:
        raise SmokeTestFailure(
            "BLUEBERRY_ADMIN_USERNAME and BLUEBERRY_ADMIN_PASSWORD are required"
        )

    unique_suffix = uuid.uuid4().hex[:8]
    with httpx.Client(base_url=base_url, timeout=10.0) as client:
        _step("GET /health")
        body = _check(client.get("/health"), 200, "health check")
        if body.get("status") != "ok":
            raise SmokeTestFailure(f"health check: unexpected body {body!r}")

        _step("POST /api/v1/auth/login")
        login = _check(
            client.post(
                "/api/v1/auth/login",
                data={"username": username, "password": password},
            ),
            200,
            "administrator login",
        )
        client.headers.update({"Authorization": f"Bearer {login['access_token']}"})

        _step("POST /api/v1/samples")
        sample = _check(
            client.post("/api/v1/samples", json={"sample_code": f"SMOKE-{unique_suffix}"}),
            201,
            "create sample",
        )
        sample_id = sample["id"]

        _step("POST /api/v1/model-versions")
        model_version = _check(
            client.post(
                "/api/v1/model-versions",
                json={
                    "name": f"smoke-engine-{unique_suffix}",
                    "version": "0.1.0",
                    "model_type": "mock",
                },
            ),
            201,
            "create model version",
        )

        petri_image = _check(
            client.post(
                f"/api/v1/samples/{sample_id}/petri-images",
                files={"file": ("colony.jpg", _make_image_bytes("JPEG", "white"), "image/jpeg")},
                data={"culture_medium": "PDA"},
            ),
            201,
            "upload petri image",
        )
        micro_image = _check(
            client.post(
                f"/api/v1/samples/{sample_id}/micro-images",
                files={"file": ("hyphae.png", _make_image_bytes("PNG", "gray"), "image/png")},
                data={"magnification": "400x"},
            ),
            201,
            "upload micro image",
        )

        analysis_run = _check(
            client.post(
                "/api/v1/analysis-runs",
                json={
                    "sample_id": sample_id,
                    "petri_image_id": petri_image["id"],
                    "micro_image_id": micro_image["id"],
                    "model_version_id": model_version["id"],
                },
            ),
            201,
            "create analysis run",
        )
        analysis_run_id = analysis_run["id"]

        fetched = _check(
            client.get(f"/api/v1/analysis-runs/{analysis_run_id}"),
            200,
            "get analysis run",
        )
        if fetched["id"] != analysis_run_id:
            raise SmokeTestFailure("analysis run id mismatch")

        processed = _check(
            client.post(f"/api/v1/analysis-runs/{analysis_run_id}/process"),
            200,
            "process analysis run",
        )
        if processed["analysis_run"]["status"] not in {"completed", "needs_review"}:
            raise SmokeTestFailure("unexpected processed analysis status")
        if processed["prediction"] is None:
            raise SmokeTestFailure("processing did not return a prediction")

        prediction = _check(
            client.get(f"/api/v1/analysis-runs/{analysis_run_id}/prediction"),
            200,
            "get prediction",
        )
        if prediction["id"] != processed["prediction"]["id"]:
            raise SmokeTestFailure("prediction id mismatch")

    print()
    print(f"SUCCESS: authenticated synchronous smoke passed against {base_url}.")
    print(f"Predicted label (simulated, non-diagnostic): {prediction['predicted_label']}")


def main() -> None:
    base_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE_URL
    try:
        run(base_url)
    except SmokeTestFailure as exc:
        print(f"FAILED: {exc}")
        sys.exit(1)
    except httpx.ConnectError as exc:
        print(f"FAILED: could not connect to {base_url}: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
