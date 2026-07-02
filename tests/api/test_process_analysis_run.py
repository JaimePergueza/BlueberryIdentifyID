import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from blueberry_microid.domain.entities.prediction import Prediction
from blueberry_microid.domain.enums.analysis_status import AnalysisStatus
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.infrastructure.db.models.prediction import PredictionModel
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_analysis_run_repository import (
    SqlAlchemyAnalysisRunRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_prediction_repository import (
    SqlAlchemyPredictionRepository,
)
from blueberry_microid.interfaces.api.v1.dependencies import get_inference_engine, get_process_analysis_run_use_case
from tests.api.image_helpers import make_valid_jpeg_bytes, make_valid_png_bytes
from tests.unit.application.fakes import FailingInferenceEngine

# Taxon-shaped words that must never appear anywhere in a process/prediction response.
_FORBIDDEN_TAXONOMY_WORDS = ("aspergillus", "penicillium", "botrytis", "escherichia", "salmonella")

_PRELIMINARY_LABELS = {
    "no_evident_growth",
    "suspicious_growth",
    "probable_fungal_growth",
    "probable_bacterial_growth",
    "inconclusive",
}


def _create_sample(api_client, sample_code: str) -> str:
    return api_client.post("/api/v1/samples", json={"sample_code": sample_code}).json()["id"]


def _create_model_version(api_client, name: str) -> str:
    return api_client.post(
        "/api/v1/model-versions", json={"name": name, "version": "0.1.0", "model_type": "mock"}
    ).json()["id"]


def _create_petri_image(api_client, sample_id: str) -> str:
    content = make_valid_jpeg_bytes()
    return api_client.post(
        f"/api/v1/samples/{sample_id}/petri-images",
        files={"file": ("colony.jpg", content, "image/jpeg")},
    ).json()["id"]


def _create_micro_image(api_client, sample_id: str) -> str:
    content = make_valid_png_bytes()
    return api_client.post(
        f"/api/v1/samples/{sample_id}/micro-images",
        files={"file": ("hyphae.png", content, "image/png")},
    ).json()["id"]


def _create_pending_run(api_client, suffix: str) -> str:
    sample_id = _create_sample(api_client, f"S-FLOW-{suffix}")
    petri_image_id = _create_petri_image(api_client, sample_id)
    micro_image_id = _create_micro_image(api_client, sample_id)
    model_version_id = _create_model_version(api_client, f"engine-flow-{suffix}")
    response = api_client.post(
        "/api/v1/analysis-runs",
        json={
            "sample_id": sample_id,
            "petri_image_id": petri_image_id,
            "micro_image_id": micro_image_id,
            "model_version_id": model_version_id,
        },
    )
    return response.json()["id"]


def _force_status(api_client, run_id: str, status: AnalysisStatus) -> None:
    """Bypass the API to directly rewrite an AnalysisRun's persisted status,
    so idempotency at every non-pending state can be tested deterministically
    without needing to reproduce real concurrent processing.
    """
    session_factory = api_client.app.state.session_factory
    with session_factory() as session:
        repository = SqlAlchemyAnalysisRunRepository(session)
        run = repository.get_by_id(uuid.UUID(run_id))
        run.status = status
        run.started_at = run.started_at or datetime.now(timezone.utc)
        if status in (AnalysisStatus.COMPLETED, AnalysisStatus.NEEDS_REVIEW, AnalysisStatus.FAILED):
            run.completed_at = run.completed_at or datetime.now(timezone.utc)
        if status == AnalysisStatus.FAILED:
            run.error_message = run.error_message or "forced failure for testing"
        repository.update(run)


def _add_prediction_for_run(api_client, run_id: str) -> None:
    session_factory = api_client.app.state.session_factory
    with session_factory() as session:
        SqlAlchemyPredictionRepository(session).add(
            Prediction(
                analysis_run_id=uuid.UUID(run_id),
                predicted_label=PredictedLabel.NO_EVIDENT_GROWTH,
                confidence_score=0.6,
            )
        )


def _count_predictions_for_run(api_client, run_id: str) -> int:
    session_factory = api_client.app.state.session_factory
    with session_factory() as session:
        statement = select(PredictionModel).where(PredictionModel.analysis_run_id == uuid.UUID(run_id))
        return len(session.execute(statement).scalars().all())


def test_full_golden_path_sample_to_processed_prediction(api_client):
    """Steps 1-7 of the required flow: sample, model version, images, run,
    process, and reading the prediction back.
    """
    run_id = _create_pending_run(api_client, "1")

    process_response = api_client.post(f"/api/v1/analysis-runs/{run_id}/process")

    assert process_response.status_code == 200
    body = process_response.json()
    assert body["analysis_run"]["id"] == run_id
    assert body["analysis_run"]["status"] in {"completed", "needs_review"}
    assert body["prediction"] is not None
    assert body["prediction"]["predicted_label"] in _PRELIMINARY_LABELS

    prediction_response = api_client.get(f"/api/v1/analysis-runs/{run_id}/prediction")
    assert prediction_response.status_code == 200
    assert prediction_response.json()["id"] == body["prediction"]["id"]


def test_reprocessing_the_same_analysis_run_is_rejected(api_client):
    run_id = _create_pending_run(api_client, "2")
    first = api_client.post(f"/api/v1/analysis-runs/{run_id}/process")
    assert first.status_code == 200

    second = api_client.post(f"/api/v1/analysis-runs/{run_id}/process")

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "analysis_run_not_processable"


def test_process_returns_404_for_missing_analysis_run(api_client):
    response = api_client.post("/api/v1/analysis-runs/00000000-0000-0000-0000-000000000000/process")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "analysis_run_not_found"


def test_prediction_not_found_before_processing(api_client):
    run_id = _create_pending_run(api_client, "3")

    response = api_client.get(f"/api/v1/analysis-runs/{run_id}/prediction")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "prediction_not_found"


def test_prediction_not_found_for_nonexistent_analysis_run(api_client):
    response = api_client.get("/api/v1/analysis-runs/00000000-0000-0000-0000-000000000000/prediction")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "prediction_not_found"


def test_process_response_makes_mock_nature_explicit(api_client):
    run_id = _create_pending_run(api_client, "4")

    response = api_client.post(f"/api/v1/analysis-runs/{run_id}/process")

    body = response.json()
    assert body["disclaimer"]
    disclaimer_and_observation = (body["disclaimer"] + " " + (body["prediction"]["technical_observation"] or "")).lower()
    assert "mock" in disclaimer_and_observation or "simulat" in disclaimer_and_observation


def test_process_response_never_exposes_species_or_genus(api_client):
    run_id = _create_pending_run(api_client, "5")

    response = api_client.post(f"/api/v1/analysis-runs/{run_id}/process")

    body = response.json()
    haystack = (
        body["disclaimer"]
        + " "
        + body["prediction"]["predicted_label"]
        + " "
        + (body["prediction"]["technical_observation"] or "")
        + " "
        + " ".join((body["prediction"]["class_probabilities"] or {}).keys())
    ).lower()
    for forbidden_word in _FORBIDDEN_TAXONOMY_WORDS:
        assert forbidden_word not in haystack
    assert body["prediction"]["predicted_label"] in _PRELIMINARY_LABELS


# --- Phase 4.5: idempotency, claim, and recovery at the API layer -------


def test_process_on_processing_status_returns_409(api_client):
    run_id = _create_pending_run(api_client, "6")
    _force_status(api_client, run_id, AnalysisStatus.PROCESSING)

    response = api_client.post(f"/api/v1/analysis-runs/{run_id}/process")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "analysis_run_not_processable"


def test_process_on_failed_status_returns_409(api_client):
    run_id = _create_pending_run(api_client, "7")
    _force_status(api_client, run_id, AnalysisStatus.FAILED)

    response = api_client.post(f"/api/v1/analysis-runs/{run_id}/process")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "analysis_run_not_processable"


def test_getting_prediction_never_creates_one(api_client):
    run_id = _create_pending_run(api_client, "8")

    for _ in range(3):
        response = api_client.get(f"/api/v1/analysis-runs/{run_id}/prediction")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "prediction_not_found"


class _AlwaysFailingProcessUseCase:
    def execute(self, *_args, **_kwargs):
        raise RuntimeError("db password=hunter2 at /var/secrets/db.conf")


def test_process_500_does_not_leak_internal_details(api_client):
    run_id = _create_pending_run(api_client, "9")
    api_client.app.dependency_overrides[get_process_analysis_run_use_case] = lambda: _AlwaysFailingProcessUseCase()
    try:
        response = api_client.post(f"/api/v1/analysis-runs/{run_id}/process")
    finally:
        api_client.app.dependency_overrides.pop(get_process_analysis_run_use_case, None)

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    message = body["error"]["message"]
    assert "hunter2" not in message
    assert "/var/secrets" not in message
    assert "RuntimeError" not in message


def test_process_with_failing_engine_returns_500_marks_failed_and_preserves_request_id(api_client):
    run_id = _create_pending_run(api_client, "11")
    api_client.app.dependency_overrides[get_inference_engine] = lambda: FailingInferenceEngine()
    try:
        response = api_client.post(
            f"/api/v1/analysis-runs/{run_id}/process",
            headers={"X-Request-ID": "engine-fail-req-1"},
        )
    finally:
        api_client.app.dependency_overrides.pop(get_inference_engine, None)

    assert response.status_code == 500
    assert response.headers["x-request-id"] == "engine-fail-req-1"
    body = response.json()
    assert body == {
        "error": {
            "code": "analysis_processing_failed",
            "message": "Analysis processing failed",
        }
    }
    assert "simulated inference engine crash" not in str(body)
    assert "RuntimeError" not in str(body)

    status_response = api_client.get(f"/api/v1/analysis-runs/{run_id}")
    assert status_response.status_code == 200
    persisted = status_response.json()
    assert persisted["status"] == "failed"
    assert persisted["error_message"] == "Analysis processing failed"


def test_process_with_duplicate_prediction_returns_409_and_does_not_leave_processing(api_client):
    run_id = _create_pending_run(api_client, "12")
    _add_prediction_for_run(api_client, run_id)

    response = api_client.post(
        f"/api/v1/analysis-runs/{run_id}/process",
        headers={"X-Request-ID": "duplicate-prediction-req-1"},
    )

    assert response.status_code == 409
    assert response.headers["x-request-id"] == "duplicate-prediction-req-1"
    assert response.json() == {
        "error": {
            "code": "duplicate_prediction",
            "message": "Prediction already exists for this analysis run",
        }
    }
    assert _count_predictions_for_run(api_client, run_id) == 1

    status_response = api_client.get(f"/api/v1/analysis-runs/{run_id}")
    assert status_response.status_code == 200
    persisted = status_response.json()
    assert persisted["status"] == "failed"
    assert persisted["status"] != "processing"
    assert persisted["error_message"] == "Prediction already exists for this analysis run"


def test_process_conflict_response_preserves_x_request_id(api_client):
    run_id = _create_pending_run(api_client, "10")
    first = api_client.post(f"/api/v1/analysis-runs/{run_id}/process")
    assert first.status_code == 200

    response = api_client.post(
        f"/api/v1/analysis-runs/{run_id}/process", headers={"X-Request-ID": "client-req-42"}
    )

    assert response.status_code == 409
    assert response.headers["x-request-id"] == "client-req-42"
