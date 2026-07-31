"""End-to-end authenticated API smoke test against REAL PostgreSQL."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from blueberry_microid.application.use_cases.auth.create_user import CreateUserUseCase
from blueberry_microid.domain.enums.user_role import UserRole
from blueberry_microid.infrastructure.config.settings import Settings
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_user_repository import (
    SqlAlchemyUserRepository,
)
from blueberry_microid.infrastructure.db.session.session_factory import create_session_factory
from blueberry_microid.infrastructure.security.pwdlib_password_hasher import PwdlibPasswordHasher
from blueberry_microid.interfaces.api.app import create_app
from tests.api.image_helpers import make_valid_jpeg_bytes, make_valid_png_bytes

pytestmark = pytest.mark.postgres

_ALL_TABLES = (
    "auth_sessions",
    "users",
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

_ADMIN_PASSWORD = "Postgres-Smoke-Administrator-42"


@pytest.fixture()
def postgres_api_client(migrated_engine, postgres_url, tmp_path):
    with migrated_engine.begin() as connection:
        connection.execute(text("TRUNCATE " + ", ".join(_ALL_TABLES) + " RESTART IDENTITY CASCADE"))

    app = create_app()
    app.state.settings = Settings(_env_file=None, storage_root=tmp_path, database_url=postgres_url)
    app.state.engine = migrated_engine
    app.state.session_factory = create_session_factory(migrated_engine)

    with app.state.session_factory() as session:
        CreateUserUseCase(
            SqlAlchemyUserRepository(session),
            PwdlibPasswordHasher(),
        ).execute("postgres-admin", _ADMIN_PASSWORD, UserRole.ADMIN)

    with TestClient(app, raise_server_exceptions=False) as client:
        login = client.post(
            "/api/v1/auth/login",
            data={"username": "postgres-admin", "password": _ADMIN_PASSWORD},
        )
        assert login.status_code == 200, login.text
        client.headers.update({"Authorization": f"Bearer {login.json()['access_token']}"})
        yield client


def test_full_flow_sample_to_final_human_review_on_postgres(postgres_api_client):
    client = postgres_api_client

    sample_response = client.post("/api/v1/samples", json={"sample_code": "S-PG-SMOKE"})
    assert sample_response.status_code == 201
    sample_id = sample_response.json()["id"]

    model_response = client.post(
        "/api/v1/model-versions",
        json={"name": "pg-smoke-engine", "version": "0.1.0", "model_type": "mock"},
    )
    assert model_response.status_code == 201
    model_version_id = model_response.json()["id"]

    petri_response = client.post(
        f"/api/v1/samples/{sample_id}/petri-images",
        files={"file": ("petri.jpg", make_valid_jpeg_bytes(), "image/jpeg")},
    )
    assert petri_response.status_code == 201
    petri_image_id = petri_response.json()["id"]

    micro_response = client.post(
        f"/api/v1/samples/{sample_id}/micro-images",
        files={"file": ("micro.png", make_valid_png_bytes(), "image/png")},
    )
    assert micro_response.status_code == 201
    micro_image_id = micro_response.json()["id"]

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

    process_response = client.post(f"/api/v1/analysis-runs/{run_id}/process")
    assert process_response.status_code == 200
    processed = process_response.json()
    assert processed["analysis_run"]["status"] in {"completed", "needs_review"}
    assert processed["prediction"]["predicted_label"] in _PRELIMINARY_LABELS

    prediction_response = client.get(f"/api/v1/analysis-runs/{run_id}/prediction")
    assert prediction_response.status_code == 200
    assert prediction_response.json()["id"] == processed["prediction"]["id"]

    review_response = client.post(
        f"/api/v1/analysis-runs/{run_id}/reviews",
        json={"reviewer_name": "dr. smith", "review_decision": "confirmed", "is_final": True},
    )
    assert review_response.status_code == 201
    review_body = review_response.json()

    final_response = client.get(f"/api/v1/analysis-runs/{run_id}/reviews/final")
    assert final_response.status_code == 200
    assert final_response.json()["id"] == review_body["id"]
