import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select

from blueberry_microid.infrastructure.config.settings import Settings, get_settings
from blueberry_microid.infrastructure.db.models import (
    AnalysisRunModel,
    Base,
    HumanReviewModel,
    MicroImageModel,
    ModelVersionModel,
    PetriImageModel,
    PredictionModel,
    SampleModel,
)
from blueberry_microid.infrastructure.db.session.session_factory import create_session_factory
from blueberry_microid.infrastructure.tasks.analysis_tasks import process_analysis_run_task
from blueberry_microid.interfaces.api.app import create_app
from blueberry_microid.interfaces.api.v1.dependencies import get_process_analysis_run_task
from tests.api.image_helpers import make_valid_jpeg_bytes, make_valid_png_bytes

_SQLITE_TABLES = [
    SampleModel.__table__,
    ModelVersionModel.__table__,
    PetriImageModel.__table__,
    MicroImageModel.__table__,
    AnalysisRunModel.__table__,
    HumanReviewModel.__table__,
    PredictionModel.__table__,
]


@pytest.fixture()
def eager_api_client(tmp_path, monkeypatch):
    database_path = tmp_path / "async.sqlite"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "storage"))
    monkeypatch.setenv("CELERY_BROKER_URL", "memory://")
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "cache+memory://")
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "true")
    monkeypatch.setenv("CELERY_TASK_EAGER_PROPAGATES", "true")
    get_settings.cache_clear()

    app = create_app()
    engine = create_engine(database_url, future=True)
    Base.metadata.create_all(engine, tables=_SQLITE_TABLES)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.settings = Settings(_env_file=None)

    process_analysis_run_task.app.conf.update(
        broker_url="memory://",
        result_backend="cache+memory://",
        task_always_eager=True,
        task_eager_propagates=True,
        task_store_eager_result=True,
    )
    app.state.celery_app = process_analysis_run_task.app

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client

    engine.dispose()
    get_settings.cache_clear()


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
    sample_id = _create_sample(api_client, f"S-ASYNC-{suffix}")
    response = api_client.post(
        "/api/v1/analysis-runs",
        json={
            "sample_id": sample_id,
            "petri_image_id": _create_petri_image(api_client, sample_id),
            "micro_image_id": _create_micro_image(api_client, sample_id),
            "model_version_id": _create_model_version(api_client, f"async-flow-{suffix}"),
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _count_predictions_for_run(api_client, run_id: str) -> int:
    session_factory = api_client.app.state.session_factory
    with session_factory() as session:
        statement = select(PredictionModel).where(PredictionModel.analysis_run_id == uuid.UUID(run_id))
        return len(session.execute(statement).scalars().all())


class _FakeQueuedTask:
    def __init__(self) -> None:
        self.called = False

    def apply_async(self, *, args, queue):
        self.called = True
        self.args = args
        self.queue = queue

        class _Result:
            id = "fake-task-id"

        return _Result()


def test_process_async_queues_without_running_inference(api_client):
    run_id = _create_pending_run(api_client, "queue-only")
    fake_task = _FakeQueuedTask()
    api_client.app.dependency_overrides[get_process_analysis_run_task] = lambda: fake_task
    try:
        response = api_client.post(
            f"/api/v1/analysis-runs/{run_id}/process-async",
            headers={"X-Request-ID": "async-req-1"},
        )
    finally:
        api_client.app.dependency_overrides.pop(get_process_analysis_run_task, None)

    assert response.status_code == 202
    assert response.headers["x-request-id"] == "async-req-1"
    assert response.json() == {
        "analysis_run_id": run_id,
        "task_id": "fake-task-id",
        "status": "queued",
        "message": "Analysis processing has been queued",
    }
    assert fake_task.called is True
    assert fake_task.args == [run_id]
    assert fake_task.queue == "analysis"
    assert _count_predictions_for_run(api_client, run_id) == 0


def test_process_async_eager_processes_analysis_and_allows_human_review(eager_api_client):
    run_id = _create_pending_run(eager_api_client, "full")

    response = eager_api_client.post(f"/api/v1/analysis-runs/{run_id}/process-async")

    assert response.status_code == 202
    task_id = response.json()["task_id"]

    status_response = eager_api_client.get(f"/api/v1/tasks/{task_id}")
    assert status_response.status_code == 200
    assert status_response.json()["task_id"] == task_id
    assert status_response.json()["state"] in {"PENDING", "SUCCESS"}

    run_response = eager_api_client.get(f"/api/v1/analysis-runs/{run_id}")
    assert run_response.status_code == 200
    assert run_response.json()["status"] in {"completed", "needs_review"}

    prediction_response = eager_api_client.get(f"/api/v1/analysis-runs/{run_id}/prediction")
    assert prediction_response.status_code == 200

    review_response = eager_api_client.post(
        f"/api/v1/analysis-runs/{run_id}/reviews",
        json={"reviewer_name": "Dra. Lopez", "review_decision": "confirmed"},
    )
    assert review_response.status_code == 201
    assert review_response.json()["is_final"] is True


def test_process_async_rejects_non_pending_run(eager_api_client):
    run_id = _create_pending_run(eager_api_client, "conflict")
    first = eager_api_client.post(f"/api/v1/analysis-runs/{run_id}/process-async")
    assert first.status_code == 202

    second = eager_api_client.post(f"/api/v1/analysis-runs/{run_id}/process-async")

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "analysis_run_not_processable"


def test_duplicate_async_tasks_do_not_create_second_prediction(eager_api_client):
    run_id = _create_pending_run(eager_api_client, "duplicate")

    first = process_analysis_run_task.run(run_id)
    second = process_analysis_run_task.run(run_id)

    assert first["status"] in {"completed", "needs_review"}
    assert second["status"] in {"completed", "needs_review"}
    assert _count_predictions_for_run(eager_api_client, run_id) == 1
