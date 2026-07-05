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


def test_dataset_snapshot_from_curation_run_exposes_manifest_provenance(api_client):
    upload = _upload(api_client)
    review = _review(api_client, upload["analysis_run_id"], "confirmed")
    curation = api_client.post(
        "/api/v1/datasets/curation-runs",
        json={"analysis_run_ids": [upload["analysis_run_id"]]},
    ).json()

    response = api_client.post(
        "/api/v1/datasets/snapshots/from-curation-run",
        json={
            "curation_run_id": curation["id"],
            "snapshot_name": "reviewed-two-image-smoke",
            "created_by": "api-test",
        },
        headers={"X-Request-ID": "snapshot-curation-req-1"},
    )

    assert response.status_code == 201
    assert response.headers["x-request-id"] == "snapshot-curation-req-1"
    body = response.json()
    assert body["status"] == "completed"
    assert body["dataset_items_created"] == 1
    assert body["provenance"]["source"] == "human_reviewed_curation_run"

    snapshot_id = body["snapshot_id"]
    items = api_client.get(f"/api/v1/datasets/snapshots/{snapshot_id}/items").json()
    assert len(items) == 1
    assert items[0]["curation_run_id"] == curation["id"]
    assert items[0]["curation_item_id"] is not None
    assert items[0]["final_review_id"] == review["id"]
    assert items[0]["ground_truth_label"] == upload["predicted_label"]
    assert items[0]["provenance"]["ground_truth_source"] == "final_human_review"

    manifest = api_client.get(f"/api/v1/datasets/snapshots/{snapshot_id}/manifest").json()
    manifest_item = manifest["items"][0]
    assert manifest_item["curation_run_id"] == curation["id"]
    assert manifest_item["curation_item_id"] == items[0]["curation_item_id"]
    assert manifest_item["provenance"]["prediction_is_ground_truth"] is False
    manifest_text = str(manifest).lower()
    assert "species" not in manifest_text
    assert "genus" not in manifest_text
    assert "diagnosis" not in manifest_text
