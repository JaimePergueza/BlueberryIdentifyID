from tests.api.image_helpers import make_valid_jpeg_bytes


def _upload(api_client):
    files = {
        "petri_image": ("petri.jpg", make_valid_jpeg_bytes(), "image/jpeg"),
        "micro_image": ("micro.jpg", make_valid_jpeg_bytes(color="green"), "image/jpeg"),
    }
    return api_client.post("/api/v1/analysis/two-image-upload", files=files).json()


def _review(api_client, run_id, decision="confirmed", corrected_label=None):
    payload = {"reviewer_name": "Expert", "review_decision": decision}
    if corrected_label is not None:
        payload["corrected_label"] = corrected_label
    return api_client.post(f"/api/v1/analysis-runs/{run_id}/reviews", json=payload).json()


def test_dataset_curation_includes_human_reviewed_two_image_analysis(api_client):
    upload = _upload(api_client)
    review = _review(api_client, upload["analysis_run_id"], "confirmed")

    response = api_client.post(
        "/api/v1/datasets/curation-runs",
        json={"analysis_run_ids": [upload["analysis_run_id"]], "create_snapshot": True},
        headers={"X-Request-ID": "curation-req-1"},
    )

    assert response.status_code == 201
    assert response.headers["x-request-id"] == "curation-req-1"
    body = response.json()
    assert body["included_count"] == 1
    assert body["excluded_count"] == 0
    assert body["created_snapshot_id"] is not None

    items = api_client.get(f"/api/v1/datasets/curation-runs/{body['id']}/items").json()
    assert len(items) == 1
    item = items[0]
    assert item["curation_status"] == "included"
    assert item["analysis_run_id"] == upload["analysis_run_id"]
    assert item["prediction_id"] == upload["prediction_id"]
    assert item["human_review_id"] == review["id"]
    assert item["final_label"] == upload["predicted_label"]
    assert item["provenance"]["prediction_is_ground_truth"] is False
    assert "species" not in str(item).lower()
    assert "genus" not in str(item).lower()


def test_dataset_curation_excludes_run_without_final_review(api_client):
    upload = _upload(api_client)

    response = api_client.post(
        "/api/v1/datasets/curation-runs",
        json={"analysis_run_ids": [upload["analysis_run_id"]]},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["included_count"] == 0
    assert body["excluded_count"] == 1
    items = api_client.get(f"/api/v1/datasets/curation-runs/{body['id']}/items").json()
    assert items[0]["curation_status"] == "excluded_pending_review"


def test_dataset_curation_requires_explicit_all_reviewed_for_global_scan(api_client):
    response = api_client.post("/api/v1/datasets/curation-runs", json={})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "dataset_curation_not_allowed"

