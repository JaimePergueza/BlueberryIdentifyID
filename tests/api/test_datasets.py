from tests.api.image_helpers import make_valid_jpeg_bytes, make_valid_png_bytes

_FORBIDDEN_TAXONOMY_WORDS = ("aspergillus", "penicillium", "botrytis", "escherichia", "salmonella")


def _create_sample(api_client, sample_code: str) -> str:
    response = api_client.post("/api/v1/samples", json={"sample_code": sample_code})
    assert response.status_code == 201
    return response.json()["id"]


def _create_model_version(api_client, name: str) -> str:
    response = api_client.post(
        "/api/v1/model-versions",
        json={"name": name, "version": "0.1.0", "model_type": "mock"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_petri_image(api_client, sample_id: str) -> str:
    response = api_client.post(
        f"/api/v1/samples/{sample_id}/petri-images",
        files={"file": ("petri.jpg", make_valid_jpeg_bytes(), "image/jpeg")},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_micro_image(api_client, sample_id: str) -> str:
    response = api_client.post(
        f"/api/v1/samples/{sample_id}/micro-images",
        files={"file": ("micro.png", make_valid_png_bytes(), "image/png")},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_full_flow_creates_dataset_snapshot_items_and_manifest(api_client):
    sample_id = _create_sample(api_client, "S-DATASET-1")
    model_version_id = _create_model_version(api_client, "dataset-flow")
    petri_image_id = _create_petri_image(api_client, sample_id)
    micro_image_id = _create_micro_image(api_client, sample_id)
    run_response = api_client.post(
        "/api/v1/analysis-runs",
        json={
            "sample_id": sample_id,
            "petri_image_id": petri_image_id,
            "micro_image_id": micro_image_id,
            "model_version_id": model_version_id,
        },
    )
    assert run_response.status_code == 201
    analysis_run_id = run_response.json()["id"]

    process_response = api_client.post(f"/api/v1/analysis-runs/{analysis_run_id}/process")
    assert process_response.status_code == 200
    prediction_label = process_response.json()["prediction"]["predicted_label"]

    review_response = api_client.post(
        f"/api/v1/analysis-runs/{analysis_run_id}/reviews",
        json={"reviewer_name": "Dra. Lopez", "review_decision": "confirmed"},
    )
    assert review_response.status_code == 201
    final_review_id = review_response.json()["id"]

    snapshot_response = api_client.post(
        "/api/v1/datasets/snapshots",
        json={"name": "curated-api", "version": "0.1.0", "created_by": "qa"},
        headers={"X-Request-ID": "dataset-request-1"},
    )
    assert snapshot_response.status_code == 201
    assert snapshot_response.headers["X-Request-ID"] == "dataset-request-1"
    snapshot = snapshot_response.json()
    assert snapshot["item_count"] == 1
    assert snapshot["label_distribution"] == {prediction_label: 1}

    get_response = api_client.get(f"/api/v1/datasets/snapshots/{snapshot['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == snapshot["id"]

    items_response = api_client.get(f"/api/v1/datasets/snapshots/{snapshot['id']}/items")
    assert items_response.status_code == 200
    items = items_response.json()
    assert len(items) == 1
    assert items[0]["analysis_run_id"] == analysis_run_id
    assert items[0]["ground_truth_label"] == prediction_label
    assert items[0]["final_review_id"] == final_review_id

    manifest_response = api_client.get(f"/api/v1/datasets/snapshots/{snapshot['id']}/manifest")
    assert manifest_response.status_code == 200
    manifest = manifest_response.json()
    assert manifest["dataset_snapshot_id"] == snapshot["id"]
    assert manifest["item_count"] == 1
    assert manifest["items"][0]["ground_truth_label"] == prediction_label
    assert manifest["items"][0]["prediction_label"] == prediction_label
    assert manifest["items"][0]["petri_image_path"]
    assert manifest["items"][0]["micro_image_path"]
    assert "content" not in str(manifest).lower()
    for word in _FORBIDDEN_TAXONOMY_WORDS:
        assert word not in str(snapshot).lower()
        assert word not in str(items).lower()
        assert word not in str(manifest).lower()

