"""API coverage for the AnalysisRun history and consolidated detail endpoints."""

from datetime import datetime, timedelta, timezone
import json
from uuid import UUID

from blueberry_microid.infrastructure.db.models.analysis_run import AnalysisRunModel
from tests.api.image_helpers import make_valid_jpeg_bytes, make_valid_png_bytes


def _upload(api_client, sample_code: str) -> dict:
    response = api_client.post(
        "/api/v1/analysis/two-image-upload",
        data={"sample_code": sample_code},
        files={
            "petri_image": ("petri.jpg", make_valid_jpeg_bytes(), "image/jpeg"),
            "micro_image": ("micro.png", make_valid_png_bytes(), "image/png"),
        },
    )
    assert response.status_code == 201
    return response.json()


def _review(api_client, analysis_run_id: str, decision: str, corrected_label: str | None = None) -> dict:
    payload = {"reviewer_name": "Dra. Historia", "review_decision": decision}
    if corrected_label is not None:
        payload["corrected_label"] = corrected_label
    response = api_client.post(f"/api/v1/analysis-runs/{analysis_run_id}/reviews", json=payload)
    assert response.status_code == 201
    return response.json()


def _set_created_at(api_client, analysis_run_id: str, created_at: datetime) -> None:
    session_factory = api_client.app.state.session_factory
    with session_factory() as session:
        analysis_run = session.get(AnalysisRunModel, UUID(analysis_run_id))
        analysis_run.created_at = created_at
        session.commit()


def test_history_is_empty_when_no_analysis_runs_exist(api_client):
    response = api_client.get("/api/v1/analysis-runs")

    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 1, "page_size": 20, "total": 0, "total_pages": 0}


def test_history_returns_descending_stable_rows_and_required_fields(api_client):
    first = _upload(api_client, "HIST-FIRST")
    second = _upload(api_client, "HIST-SECOND")
    now = datetime.now(timezone.utc)
    _set_created_at(api_client, first["analysis_run_id"], now - timedelta(minutes=1))
    _set_created_at(api_client, second["analysis_run_id"], now)

    response = api_client.get("/api/v1/analysis-runs")

    assert response.status_code == 200
    body = response.json()
    assert [item["analysis_run_id"] for item in body["items"]] == [
        second["analysis_run_id"],
        first["analysis_run_id"],
    ]
    assert {
        "analysis_run_id",
        "sample_id",
        "sample_code",
        "petri_image_id",
        "micro_image_id",
        "model_version_id",
        "model_name",
        "model_version",
        "model_type",
        "analysis_status",
        "created_at",
        "completed_at",
        "preliminary_label",
        "confidence_score",
        "requires_human_review",
        "review_status",
        "final_review_id",
        "review_decision",
        "reviewer_name",
        "reviewed_at",
        "final_label",
        "final_status",
    } <= set(body["items"][0])


def test_history_paginates_across_pages(api_client):
    uploads = [_upload(api_client, f"PAGE-{index}") for index in range(3)]
    now = datetime.now(timezone.utc)
    for index, upload in enumerate(uploads):
        _set_created_at(api_client, upload["analysis_run_id"], now + timedelta(seconds=index))

    first_page = api_client.get("/api/v1/analysis-runs?page=1&page_size=2").json()
    second_page = api_client.get("/api/v1/analysis-runs?page=2&page_size=2").json()

    assert first_page["total"] == 3
    assert first_page["total_pages"] == 2
    assert len(first_page["items"]) == 2
    assert len(second_page["items"]) == 1
    assert {item["analysis_run_id"] for item in first_page["items"]}.isdisjoint(
        {item["analysis_run_id"] for item in second_page["items"]}
    )


def test_history_filters_by_partial_case_insensitive_sample_code(api_client):
    wanted = _upload(api_client, "Blue-Trace-42")
    _upload(api_client, "OTHER-42")

    response = api_client.get("/api/v1/analysis-runs?sample_code=trace")

    assert response.status_code == 200
    assert [item["analysis_run_id"] for item in response.json()["items"]] == [wanted["analysis_run_id"]]


def test_history_filters_by_analysis_status(api_client):
    uploaded = _upload(api_client, "STATUS-1")

    response = api_client.get("/api/v1/analysis-runs?status=needs_review")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["analysis_run_id"] == uploaded["analysis_run_id"]


def test_history_filters_by_review_status(api_client):
    pending = _upload(api_client, "REVIEW-PENDING")
    reviewed = _upload(api_client, "REVIEWED")
    _review(api_client, reviewed["analysis_run_id"], "confirmed")

    pending_response = api_client.get("/api/v1/analysis-runs?review_status=pending").json()
    reviewed_response = api_client.get("/api/v1/analysis-runs?review_status=reviewed").json()

    assert [item["analysis_run_id"] for item in pending_response["items"]] == [pending["analysis_run_id"]]
    assert [item["analysis_run_id"] for item in reviewed_response["items"]] == [reviewed["analysis_run_id"]]


def test_history_filters_by_preliminary_and_derived_final_labels(api_client):
    uploaded = _upload(api_client, "LABELS-1")
    _review(api_client, uploaded["analysis_run_id"], "corrected", "no_evident_growth")

    preliminary = api_client.get(
        f"/api/v1/analysis-runs?preliminary_label={uploaded['predicted_label']}"
    ).json()
    final = api_client.get("/api/v1/analysis-runs?final_label=no_evident_growth").json()

    assert uploaded["analysis_run_id"] in {item["analysis_run_id"] for item in preliminary["items"]}
    assert [item["analysis_run_id"] for item in final["items"]] == [uploaded["analysis_run_id"]]
    assert final["items"][0]["final_label"] == "no_evident_growth"


def test_history_filters_by_created_range_and_combination(api_client):
    old = _upload(api_client, "RANGE-OLD")
    current = _upload(api_client, "Range-Current")
    now = datetime.now(timezone.utc)
    _set_created_at(api_client, old["analysis_run_id"], now - timedelta(days=2))
    _set_created_at(api_client, current["analysis_run_id"], now)
    _review(api_client, current["analysis_run_id"], "confirmed")

    start = (now - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    end = (now + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    range_response = api_client.get(f"/api/v1/analysis-runs?created_from={start}&created_to={end}").json()
    combined = api_client.get(
        f"/api/v1/analysis-runs?sample_code=current&status=needs_review&review_status=reviewed&created_from={start}"
    ).json()

    assert [item["analysis_run_id"] for item in range_response["items"]] == [current["analysis_run_id"]]
    assert [item["analysis_run_id"] for item in combined["items"]] == [current["analysis_run_id"]]


def test_detail_without_review_and_with_final_review(api_client):
    pending = _upload(api_client, "DETAIL-PENDING")
    reviewed = _upload(api_client, "DETAIL-REVIEWED")
    review = _review(api_client, reviewed["analysis_run_id"], "marked_inconclusive")

    pending_detail = api_client.get(f"/api/v1/analysis-runs/{pending['analysis_run_id']}/detail")
    reviewed_detail = api_client.get(f"/api/v1/analysis-runs/{reviewed['analysis_run_id']}/detail")

    assert pending_detail.status_code == 200
    assert pending_detail.json()["human_review"] is None
    assert pending_detail.json()["final_status"] == "pending_human_review"
    assert reviewed_detail.status_code == 200
    assert reviewed_detail.json()["human_review"]["id"] == review["id"]
    assert reviewed_detail.json()["final_label"] == "inconclusive"
    assert reviewed_detail.json()["final_status"] == "inconclusive"


def test_detail_unknown_analysis_run_uses_controlled_not_found_error(api_client):
    response = api_client.get("/api/v1/analysis-runs/00000000-0000-0000-0000-000000000000/detail")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "analysis_run_not_found"


def test_history_and_detail_never_serialize_file_path(api_client):
    uploaded = _upload(api_client, "SAFE-PATH")

    history = api_client.get("/api/v1/analysis-runs").json()
    detail = api_client.get(f"/api/v1/analysis-runs/{uploaded['analysis_run_id']}/detail").json()

    assert "file_path" not in json.dumps(history).lower()
    assert "file_path" not in json.dumps(detail).lower()


def test_history_rejects_invalid_pagination_dates_and_enums(api_client):
    invalid_page = api_client.get("/api/v1/analysis-runs?page=0")
    invalid_page_size = api_client.get("/api/v1/analysis-runs?page_size=101")
    invalid_status = api_client.get("/api/v1/analysis-runs?status=not-a-status")
    invalid_label = api_client.get("/api/v1/analysis-runs?final_label=not-a-label")
    invalid_dates = api_client.get(
        "/api/v1/analysis-runs?created_from=2026-01-02T00:00:00Z&created_to=2026-01-01T00:00:00Z"
    )

    for response in (invalid_page, invalid_page_size, invalid_status, invalid_label, invalid_dates):
        assert response.status_code == 422
