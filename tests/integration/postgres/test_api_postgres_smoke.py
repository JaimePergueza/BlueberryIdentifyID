"""End-to-end API smoke test against a REAL PostgreSQL database.

Drives the actual FastAPI app (via TestClient) pointed at the migrated
PostgreSQL database and a temporary storage directory, exercising the full
happy path: sample -> images -> analysis run -> mock processing ->
prediction -> final human review. This proves the whole stack — routers,
use cases, SQLAlchemy repositories, JSONB, enums, transactions — works on
PostgreSQL, not only on SQLite.

Still uses only the deterministic mock inference engine and Pillow-generated
images: no real AI, no datasets, no taxonomy.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from blueberry_microid.infrastructure.config.settings import Settings
from blueberry_microid.infrastructure.db.session.session_factory import create_session_factory
from blueberry_microid.interfaces.api.app import create_app
from tests.api.image_helpers import make_valid_jpeg_bytes, make_valid_png_bytes

pytestmark = pytest.mark.postgres

_ALL_TABLES = (
    "human_reviews",
    "predictions",
    "analysis_runs",
    "micro_images",
    "petri_images",
    "model_versions",
    "samples",
)

_PRELIMINARY_LABELS = {
    "no_evident_growth",
    "suspicious_growth",
    "probable_fungal_growth",
    "probable_bacterial_growth",
    "inconclusive",
}


@pytest.fixture()
def postgres_api_client(migrated_engine, postgres_url, tmp_path):
    # Start from a clean database so this flow is deterministic regardless of
    # what other tests in the session did.
    with migrated_engine.begin() as connection:
        connection.execute(text("TRUNCATE " + ", ".join(_ALL_TABLES) + " RESTART IDENTITY CASCADE"))

    app = create_app()
    # Point the app at the real PostgreSQL engine and a temp storage dir,
    # rather than whatever the process environment would otherwise use.
    app.state.settings = Settings(_env_file=None, storage_root=tmp_path, database_url=postgres_url)
    app.state.engine = migrated_engine
    app.state.session_factory = create_session_factory(migrated_engine)

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def test_full_flow_sample_to_final_human_review_on_postgres(postgres_api_client):
    client = postgres_api_client

    # 1. create sample
    sample_id = client.post("/api/v1/samples", json={"sample_code": "S-PG-SMOKE"}).json()["id"]

    # 2. create a mock model version
    model_version_id = client.post(
        "/api/v1/model-versions",
        json={"name": "pg-smoke-engine", "version": "0.1.0", "model_type": "mock"},
    ).json()["id"]

    # 3. upload a Petri dish image (Pillow-generated, no real dataset)
    petri_image_id = client.post(
        f"/api/v1/samples/{sample_id}/petri-images",
        files={"file": ("petri.jpg", make_valid_jpeg_bytes(), "image/jpeg")},
    ).json()["id"]

    # 4. upload a microscopy image
    micro_image_id = client.post(
        f"/api/v1/samples/{sample_id}/micro-images",
        files={"file": ("micro.png", make_valid_png_bytes(), "image/png")},
    ).json()["id"]

    # 5. create an AnalysisRun
    run_response = client.post(
        "/api/v1/analysis-runs",
        json={
            "sample_id": sample_id,
            "petri_image_id": petri_image_id,
            "micro_image_id": micro_image_id,
            "model_version_id": model_version_id,
        },
    )
    assert run_response.status_code == 201
    run_id = run_response.json()["id"]

    # 6. process with the mock engine
    process_response = client.post(f"/api/v1/analysis-runs/{run_id}/process")
    assert process_response.status_code == 200
    processed = process_response.json()
    assert processed["analysis_run"]["status"] in {"completed", "needs_review"}
    assert processed["prediction"]["predicted_label"] in _PRELIMINARY_LABELS

    # 7. read the Prediction back
    prediction_response = client.get(f"/api/v1/analysis-runs/{run_id}/prediction")
    assert prediction_response.status_code == 200
    assert prediction_response.json()["id"] == processed["prediction"]["id"]

    # 8. submit a final human review
    review_response = client.post(
        f"/api/v1/analysis-runs/{run_id}/reviews",
        json={"reviewer_name": "dr. smith", "review_decision": "confirmed", "is_final": True},
    )
    assert review_response.status_code == 201
    review_body = review_response.json()
    assert review_body["is_final"] is True

    # 9. read the current final human review
    final_response = client.get(f"/api/v1/analysis-runs/{run_id}/reviews/final")
    assert final_response.status_code == 200
    assert final_response.json()["id"] == review_body["id"]
