"""PostgreSQL integration tests for the final-result endpoint (Fase 42).

Exercises the full stack (FastAPI → SQLAlchemy → PostgreSQL) for:
- two-image-upload → final-result before/after review
- HumanReview persistence and resolution against real PostgreSQL
- Prediction immutability after review
- JSONB fields (feature_summary, quality_summary, decision_trace) survive
  round-trip through PostgreSQL

Still uses Pillow-generated images and the classical heuristic engine.
No real AI, no taxonomy, no training.
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

_VALID_LABELS = {
    "no_evident_growth", "suspicious_growth",
    "probable_fungal_growth", "probable_bacterial_growth", "inconclusive",
}


@pytest.fixture()
def pg_client(migrated_engine, postgres_url, tmp_path):
    with migrated_engine.begin() as connection:
        connection.execute(
            text("TRUNCATE " + ", ".join(_ALL_TABLES) + " RESTART IDENTITY CASCADE")
        )
    app = create_app()
    app.state.settings = Settings(_env_file=None, storage_root=tmp_path, database_url=postgres_url)
    app.state.engine = migrated_engine
    app.state.session_factory = create_session_factory(migrated_engine)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def _upload(client):
    return client.post(
        "/api/v1/analysis/two-image-upload",
        files={
            "petri_image": ("petri.jpg", make_valid_jpeg_bytes(), "image/jpeg"),
            "micro_image": ("micro.jpg", make_valid_jpeg_bytes(color="green"), "image/jpeg"),
        },
    )


def _review(client, run_id, decision, corrected_label=None, comments=None):
    payload = {"reviewer_name": "Dr. PG Test", "review_decision": decision}
    if corrected_label:
        payload["corrected_label"] = corrected_label
    if comments:
        payload["comments"] = comments
    return client.post(f"/api/v1/analysis-runs/{run_id}/reviews", json=payload)


# ─────────────────────────────────────────────────────────────────────────────

def test_two_image_upload_and_final_result_pending_on_postgres(pg_client):
    body = _upload(pg_client).json()
    run_id = body["analysis_run_id"]

    result = pg_client.get(f"/api/v1/analysis-runs/{run_id}/final-result")
    assert result.status_code == 200

    r = result.json()
    assert r["status"] == "pending_human_review"
    assert r["final_label"] is None
    assert r["preliminary_label"] in _VALID_LABELS
    assert r["human_review_completed"] is False
    assert r["requires_human_review"] is True


def test_jsonb_fields_survive_postgres_roundtrip(pg_client):
    """feature_summary, quality_summary and decision_trace persist as JSONB."""
    body = _upload(pg_client).json()
    run_id = body["analysis_run_id"]

    result = pg_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    assert result["feature_summary"] is not None
    assert "petri" in result["feature_summary"]
    assert result["quality_summary"] is not None
    assert "petri_is_sharp" in result["quality_summary"]
    assert isinstance(result["decision_trace"], list)
    assert len(result["decision_trace"]) >= 3


def test_confirmed_review_persists_on_postgres(pg_client):
    body = _upload(pg_client).json()
    run_id = body["analysis_run_id"]
    preliminary_label = body["predicted_label"]

    rev = _review(pg_client, run_id, "confirmed").json()
    assert rev["review_decision"] == "confirmed"

    result = pg_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    assert result["status"] == "human_confirmed"
    assert result["final_label"] == preliminary_label
    assert result["human_review_completed"] is True


def test_corrected_review_persists_on_postgres(pg_client):
    body = _upload(pg_client).json()
    run_id = body["analysis_run_id"]

    _review(pg_client, run_id, "corrected", corrected_label="no_evident_growth")

    result = pg_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    assert result["status"] == "human_corrected"
    assert result["final_label"] == "no_evident_growth"
    assert result["corrected_label"] == "no_evident_growth"


def test_prediction_not_mutated_after_review_on_postgres(pg_client):
    body = _upload(pg_client).json()
    run_id = body["analysis_run_id"]
    original_prediction_id = body["prediction_id"]
    original_label = body["predicted_label"]

    _review(pg_client, run_id, "corrected", corrected_label="probable_bacterial_growth")

    result = pg_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    assert result["prediction_id"] == original_prediction_id
    assert result["preliminary_label"] == original_label  # unchanged


def test_rejected_invalid_sample_on_postgres(pg_client):
    body = _upload(pg_client).json()
    run_id = body["analysis_run_id"]

    _review(pg_client, run_id, "rejected_invalid_sample",
            comments="Plate was contaminated.")

    result = pg_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    assert result["status"] == "rejected_invalid_sample"
    assert result["final_label"] is None
    assert result["human_review_completed"] is True


def test_inconclusive_review_on_postgres(pg_client):
    body = _upload(pg_client).json()
    run_id = body["analysis_run_id"]

    _review(pg_client, run_id, "marked_inconclusive", corrected_label="inconclusive")

    result = pg_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    assert result["status"] == "inconclusive"
    assert result["final_label"] == "inconclusive"


def test_preliminary_result_review_status_on_postgres(pg_client):
    body = _upload(pg_client).json()
    run_id = body["analysis_run_id"]

    # Before review
    prelim = pg_client.get(f"/api/v1/analysis-runs/{run_id}/preliminary-result").json()
    assert prelim["human_review_status"] == "pending_human_review"
    assert prelim["human_review_completed"] is False

    _review(pg_client, run_id, "confirmed")

    # After review
    prelim2 = pg_client.get(f"/api/v1/analysis-runs/{run_id}/preliminary-result").json()
    assert prelim2["human_review_status"] == "human_confirmed"
    assert prelim2["human_review_completed"] is True
    assert prelim2["final_label"] is not None


def test_get_reviews_returns_list_on_postgres(pg_client):
    body = _upload(pg_client).json()
    run_id = body["analysis_run_id"]

    empty = pg_client.get(f"/api/v1/analysis-runs/{run_id}/reviews").json()
    assert empty["reviews"] == []

    _review(pg_client, run_id, "confirmed")

    with_review = pg_client.get(f"/api/v1/analysis-runs/{run_id}/reviews").json()
    assert len(with_review["reviews"]) == 1
    assert with_review["reviews"][0]["review_decision"] == "confirmed"


def test_no_auto_human_review_after_upload_on_postgres(pg_client):
    body = _upload(pg_client).json()
    run_id = body["analysis_run_id"]

    reviews = pg_client.get(f"/api/v1/analysis-runs/{run_id}/reviews").json()
    assert reviews["reviews"] == []
