import uuid
from datetime import datetime, timezone

from blueberry_microid.domain.enums.analysis_status import AnalysisStatus
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_analysis_run_repository import (
    SqlAlchemyAnalysisRunRepository,
)
from tests.api.image_helpers import make_valid_jpeg_bytes, make_valid_png_bytes

_FORBIDDEN_TAXONOMY_WORDS = ("aspergillus", "penicillium", "botrytis", "escherichia", "salmonella")


def _create_sample(api_client, sample_code: str) -> str:
    return api_client.post("/api/v1/samples", json={"sample_code": sample_code}).json()["id"]


def _create_model_version(api_client, name: str) -> str:
    return api_client.post(
        "/api/v1/model-versions", json={"name": name, "version": "0.1.0", "model_type": "mock"}
    ).json()["id"]


def _create_petri_image(api_client, sample_id: str) -> str:
    return api_client.post(
        f"/api/v1/samples/{sample_id}/petri-images",
        files={"file": ("petri.jpg", make_valid_jpeg_bytes(), "image/jpeg")},
    ).json()["id"]


def _create_micro_image(api_client, sample_id: str) -> str:
    return api_client.post(
        f"/api/v1/samples/{sample_id}/micro-images",
        files={"file": ("micro.png", make_valid_png_bytes(), "image/png")},
    ).json()["id"]


def _create_pending_run(api_client, suffix: str) -> str:
    sample_id = _create_sample(api_client, f"S-REVIEW-{suffix}")
    response = api_client.post(
        "/api/v1/analysis-runs",
        json={
            "sample_id": sample_id,
            "petri_image_id": _create_petri_image(api_client, sample_id),
            "micro_image_id": _create_micro_image(api_client, sample_id),
            "model_version_id": _create_model_version(api_client, f"review-flow-{suffix}"),
        },
    )
    return response.json()["id"]


def _create_processed_run(api_client, suffix: str) -> tuple[str, dict]:
    run_id = _create_pending_run(api_client, suffix)
    process_response = api_client.post(f"/api/v1/analysis-runs/{run_id}/process")
    assert process_response.status_code == 200
    prediction_response = api_client.get(f"/api/v1/analysis-runs/{run_id}/prediction")
    assert prediction_response.status_code == 200
    return run_id, prediction_response.json()


def _force_status(api_client, run_id: str, status: AnalysisStatus) -> None:
    session_factory = api_client.app.state.session_factory
    with session_factory() as session:
        repository = SqlAlchemyAnalysisRunRepository(session)
        run = repository.get_by_id(uuid.UUID(run_id))
        run.status = status
        run.started_at = run.started_at or datetime.now(timezone.utc)
        if status in (AnalysisStatus.COMPLETED, AnalysisStatus.NEEDS_REVIEW, AnalysisStatus.FAILED):
            run.completed_at = run.completed_at or datetime.now(timezone.utc)
        repository.update(run)


def test_full_flow_creates_final_human_review(api_client):
    run_id, _prediction = _create_processed_run(api_client, "1")

    response = api_client.post(
        f"/api/v1/analysis-runs/{run_id}/reviews",
        json={
            "reviewer_name": "Dra. Lopez",
            "review_decision": "confirmed",
            "comments": "Prediction is acceptable as a broad preliminary category.",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["analysis_run_id"] == run_id
    assert body["review_decision"] == "confirmed"
    assert body["corrected_label"] is None
    assert body["is_final"] is True


def test_get_final_human_review(api_client):
    run_id, _prediction = _create_processed_run(api_client, "2")
    created = api_client.post(
        f"/api/v1/analysis-runs/{run_id}/reviews",
        json={"reviewer_name": "Dra. Lopez", "review_decision": "confirmed"},
    ).json()

    response = api_client.get(f"/api/v1/analysis-runs/{run_id}/reviews/final")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_final_human_review_returns_404_when_none_exists(api_client):
    run_id, _prediction = _create_processed_run(api_client, "2b")

    response = api_client.get(f"/api/v1/analysis-runs/{run_id}/reviews/final")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "human_review_not_found"


def test_list_human_review_history(api_client):
    run_id, _prediction = _create_processed_run(api_client, "3")
    first = api_client.post(
        f"/api/v1/analysis-runs/{run_id}/reviews",
        json={"reviewer_name": "Dra. Lopez", "review_decision": "confirmed", "is_final": False},
    ).json()
    second = api_client.post(
        f"/api/v1/analysis-runs/{run_id}/reviews",
        json={
            "reviewer_name": "Dr. Perez",
            "review_decision": "marked_inconclusive",
            "corrected_label": "inconclusive",
        },
    ).json()

    response = api_client.get(f"/api/v1/analysis-runs/{run_id}/reviews")

    assert response.status_code == 200
    assert [review["id"] for review in response.json()["reviews"]] == [first["id"], second["id"]]


def test_list_human_reviews_returns_empty_list_when_none_exist(api_client):
    run_id, _prediction = _create_processed_run(api_client, "3b")

    response = api_client.get(f"/api/v1/analysis-runs/{run_id}/reviews")

    assert response.status_code == 200
    assert response.json() == {"reviews": []}


def test_second_final_review_replaces_previous_final(api_client):
    run_id, _prediction = _create_processed_run(api_client, "4")
    first = api_client.post(
        f"/api/v1/analysis-runs/{run_id}/reviews",
        json={"reviewer_name": "Dra. Lopez", "review_decision": "confirmed"},
    ).json()
    second = api_client.post(
        f"/api/v1/analysis-runs/{run_id}/reviews",
        json={
            "reviewer_name": "Dr. Perez",
            "review_decision": "corrected",
            "corrected_label": "no_evident_growth",
        },
    ).json()

    final_response = api_client.get(f"/api/v1/analysis-runs/{run_id}/reviews/final")
    history_response = api_client.get(f"/api/v1/analysis-runs/{run_id}/reviews")

    assert final_response.status_code == 200
    assert final_response.json()["id"] == second["id"]
    history = {review["id"]: review for review in history_response.json()["reviews"]}
    assert history[first["id"]]["is_final"] is False
    assert history[second["id"]]["is_final"] is True


def test_rejects_corrected_review_without_corrected_label(api_client):
    run_id, _prediction = _create_processed_run(api_client, "5")

    response = api_client.post(
        f"/api/v1/analysis-runs/{run_id}/reviews",
        json={"reviewer_name": "Dra. Lopez", "review_decision": "corrected"},
    )

    assert response.status_code == 422


def test_rejects_review_when_prediction_does_not_exist(api_client):
    run_id = _create_pending_run(api_client, "6")
    _force_status(api_client, run_id, AnalysisStatus.COMPLETED)

    response = api_client.post(
        f"/api/v1/analysis-runs/{run_id}/reviews",
        json={"reviewer_name": "Dra. Lopez", "review_decision": "confirmed"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "prediction_not_found"


def test_rejects_review_when_analysis_run_is_pending(api_client):
    run_id = _create_pending_run(api_client, "7")

    response = api_client.post(
        f"/api/v1/analysis-runs/{run_id}/reviews",
        json={"reviewer_name": "Dra. Lopez", "review_decision": "confirmed"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "analysis_run_not_reviewable"


def test_human_review_does_not_modify_original_prediction(api_client):
    run_id, original_prediction = _create_processed_run(api_client, "8")

    response = api_client.post(
        f"/api/v1/analysis-runs/{run_id}/reviews",
        json={
            "reviewer_name": "Dra. Lopez",
            "review_decision": "corrected",
            "corrected_label": "no_evident_growth",
        },
    )
    assert response.status_code == 201

    after = api_client.get(f"/api/v1/analysis-runs/{run_id}/prediction").json()
    assert after == original_prediction


def test_human_review_response_never_exposes_species_or_genus(api_client):
    run_id, _prediction = _create_processed_run(api_client, "9")

    response = api_client.post(
        f"/api/v1/analysis-runs/{run_id}/reviews",
        json={
            "reviewer_name": "Dra. Lopez",
            "review_decision": "marked_inconclusive",
            "corrected_label": "inconclusive",
            "comments": "Broad category remains inconclusive.",
        },
    )

    haystack = str(response.json()).lower()
    for forbidden_word in _FORBIDDEN_TAXONOMY_WORDS:
        assert forbidden_word not in haystack


def test_human_review_preserves_x_request_id(api_client):
    run_id, _prediction = _create_processed_run(api_client, "10")

    response = api_client.post(
        f"/api/v1/analysis-runs/{run_id}/reviews",
        headers={"X-Request-ID": "review-req-42"},
        json={"reviewer_name": "Dra. Lopez", "review_decision": "confirmed"},
    )

    assert response.status_code == 201
    assert response.headers["x-request-id"] == "review-req-42"
