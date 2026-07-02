#!/usr/bin/env python
"""Operational smoke test for a running BlueberryMicroID API instance.

Run the API first:
    uvicorn blueberry_microid.interfaces.api.app:create_app --factory --reload

Then, in another terminal (same virtualenv):
    python scripts/api_smoke_test.py [base_url]

`base_url` defaults to http://127.0.0.1:8000.

What this does:
    1. GET  /health
    2. POST /api/v1/samples                                    (create a sample)
    3. POST /api/v1/model-versions                              (create a 'mock' model version)
    4. POST /api/v1/samples/{id}/petri-images                   (upload a Petri dish image)
    5. POST /api/v1/samples/{id}/micro-images                   (upload a microscopy image)
    6. POST /api/v1/analysis-runs                                (create a pending AnalysisRun)
    7. GET  /api/v1/analysis-runs/{id}                            (read it back)
    8. POST /api/v1/analysis-runs/{id}/process                    (run the simulated inference engine)
    9. GET  /api/v1/analysis-runs/{id}/prediction                 (read the resulting Prediction)

No external files or datasets are used: both images are tiny, solid-color
JPEG/PNG images generated in memory with Pillow, purely to exercise the
upload path. Step 8 only ever runs `MockInferenceEngine` — a deterministic
simulation with no real image analysis and no diagnostic or taxonomic
validity, never a real or trained model.

Exits with status 0 if every step passes, 1 otherwise, printing exactly
which step failed and why.
"""

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
    client = httpx.Client(base_url=base_url, timeout=10.0)
    unique_suffix = uuid.uuid4().hex[:8]

    _step("GET /health")
    body = _check(client.get("/health"), 200, "health check")
    if body.get("status") != "ok":
        raise SmokeTestFailure(f"health check: unexpected body {body!r}")

    _step("POST /api/v1/samples (create sample)")
    sample = _check(
        client.post("/api/v1/samples", json={"sample_code": f"SMOKE-{unique_suffix}"}),
        201,
        "create sample",
    )
    sample_id = sample["id"]

    _step("POST /api/v1/model-versions (create 'mock' model version)")
    model_version = _check(
        client.post(
            "/api/v1/model-versions",
            json={"name": f"smoke-engine-{unique_suffix}", "version": "0.1.0", "model_type": "mock"},
        ),
        201,
        "create model version",
    )
    model_version_id = model_version["id"]

    _step("POST /api/v1/samples/{sample_id}/petri-images (upload Petri dish image)")
    petri_content = _make_image_bytes("JPEG", "white")
    petri_image = _check(
        client.post(
            f"/api/v1/samples/{sample_id}/petri-images",
            files={"file": ("colony.jpg", petri_content, "image/jpeg")},
            data={"culture_medium": "PDA"},
        ),
        201,
        "upload petri image",
    )
    petri_image_id = petri_image["id"]

    _step("POST /api/v1/samples/{sample_id}/micro-images (upload microscopy image)")
    micro_content = _make_image_bytes("PNG", "gray")
    micro_image = _check(
        client.post(
            f"/api/v1/samples/{sample_id}/micro-images",
            files={"file": ("hyphae.png", micro_content, "image/png")},
            data={"magnification": "400x"},
        ),
        201,
        "upload micro image",
    )
    micro_image_id = micro_image["id"]

    _step("POST /api/v1/analysis-runs (create pending analysis run)")
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
        raise SmokeTestFailure(f"analysis run: expected status 'pending', got {analysis_run['status']!r}")

    _step("GET /api/v1/analysis-runs/{analysis_run_id}")
    fetched = _check(client.get(f"/api/v1/analysis-runs/{analysis_run_id}"), 200, "get analysis run")
    if fetched["id"] != analysis_run_id:
        raise SmokeTestFailure("get analysis run: id in response does not match the one just created")

    _step("POST /api/v1/analysis-runs/{analysis_run_id}/process (run the simulated inference engine)")
    processed = _check(client.post(f"/api/v1/analysis-runs/{analysis_run_id}/process"), 200, "process analysis run")
    if processed["analysis_run"]["status"] not in {"completed", "needs_review"}:
        raise SmokeTestFailure(f"process analysis run: unexpected status {processed['analysis_run']['status']!r}")
    if not processed.get("disclaimer"):
        raise SmokeTestFailure("process analysis run: response is missing the mock-engine disclaimer")
    if processed["prediction"] is None:
        raise SmokeTestFailure("process analysis run: expected a prediction, got none")

    _step("GET /api/v1/analysis-runs/{analysis_run_id}/prediction")
    prediction = _check(client.get(f"/api/v1/analysis-runs/{analysis_run_id}/prediction"), 200, "get prediction")
    if prediction["id"] != processed["prediction"]["id"]:
        raise SmokeTestFailure("get prediction: id does not match the one returned by /process")

    print()
    print(f"SUCCESS: all 9 steps passed against {base_url}.")
    print(f"Predicted label (simulated, non-diagnostic): {prediction['predicted_label']}")
    print("Reminder: this result came from MockInferenceEngine, a deterministic simulation.")
    print("It performs no real image analysis and never identifies a species or genus.")


def main() -> None:
    base_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE_URL
    try:
        run(base_url)
    except SmokeTestFailure as exc:
        print(f"FAILED: {exc}")
        sys.exit(1)
    except httpx.ConnectError as exc:
        print(f"FAILED: could not connect to {base_url}: {exc}")
        print("Is the API running? Try:")
        print("  uvicorn blueberry_microid.interfaces.api.app:create_app --factory --reload")
        sys.exit(1)


if __name__ == "__main__":
    main()
