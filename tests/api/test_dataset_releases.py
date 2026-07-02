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


def test_full_flow_creates_dataset_release_with_splits_and_manifest(api_client):
    # 1-6. sample, mock model, images, AnalysisRun, process, final HumanReview
    sample_id = _create_sample(api_client, "S-RELEASE-1")
    model_version_id = _create_model_version(api_client, "release-flow")
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
        json={"reviewer_name": "Dr. Torres", "review_decision": "confirmed"},
    )
    assert review_response.status_code == 201

    # 7. DatasetSnapshot
    snapshot_response = api_client.post(
        "/api/v1/datasets/snapshots",
        json={"name": "curated-release-api", "version": "0.1.0", "created_by": "qa"},
    )
    assert snapshot_response.status_code == 201
    snapshot = snapshot_response.json()
    assert snapshot["item_count"] == 1

    # 8. DatasetRelease
    release_response = api_client.post(
        "/api/v1/datasets/releases",
        json={
            "dataset_snapshot_id": snapshot["id"],
            "name": "release-api",
            "version": "0.1.0",
            "random_seed": 42,
            "created_by": "qa",
        },
        headers={"X-Request-ID": "release-request-1"},
    )
    assert release_response.status_code == 201
    assert release_response.headers["X-Request-ID"] == "release-request-1"
    release = release_response.json()
    assert release["dataset_snapshot_id"] == snapshot["id"]
    assert release["item_count"] == 1
    # With a single sample and default-shaped ratios, the lone item is
    # deterministically assigned to `test` regardless of seed (train/val
    # counts truncate to 0 before test absorbs the remainder).
    assert release["train_count"] + release["validation_count"] + release["test_count"] == 1

    # 9. consultar release
    get_response = api_client.get(f"/api/v1/datasets/releases/{release['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == release["id"]

    list_response = api_client.get("/api/v1/datasets/releases")
    assert list_response.status_code == 200
    assert any(item["id"] == release["id"] for item in list_response.json())

    # 10. listar split items
    items_response = api_client.get(f"/api/v1/datasets/releases/{release['id']}/items")
    assert items_response.status_code == 200
    split_items = items_response.json()
    assert len(split_items) == 1
    split_item = split_items[0]
    assert split_item["dataset_release_id"] == release["id"]

    # 12. verificar split
    assert split_item["split"] == "test"

    # 13. verificar ground_truth_label
    assert split_item["ground_truth_label"] == prediction_label

    # 11. descargar manifest
    manifest_response = api_client.get(f"/api/v1/datasets/releases/{release['id']}/manifest")
    assert manifest_response.status_code == 200
    manifest = manifest_response.json()
    assert manifest["dataset_release_id"] == release["id"]
    assert manifest["dataset_snapshot_id"] == snapshot["id"]
    assert manifest["counts"]["total"] == 1
    assert manifest["items"][0]["split"] == "test"
    assert manifest["items"][0]["analysis_run_id"] == analysis_run_id
    assert manifest["items"][0]["ground_truth_label"] == prediction_label
    assert manifest["items"][0]["prediction_label"] == prediction_label

    # 14. verificar que no hay taxonomía ni contenido binario
    haystack = str(release) + str(split_items) + str(manifest)
    for word in _FORBIDDEN_TAXONOMY_WORDS:
        assert word not in haystack.lower()
    assert "content" not in haystack.lower()


def test_create_release_returns_404_for_missing_snapshot(api_client):
    response = api_client.post(
        "/api/v1/datasets/releases",
        json={
            "dataset_snapshot_id": "00000000-0000-0000-0000-000000000000",
            "name": "orphan-release",
            "version": "0.1.0",
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "dataset_snapshot_not_found"


def test_create_release_returns_409_for_empty_snapshot(api_client):
    snapshot_response = api_client.post(
        "/api/v1/datasets/snapshots", json={"name": "empty-snapshot", "version": "0.1.0"}
    )
    assert snapshot_response.status_code == 201
    snapshot_id = snapshot_response.json()["id"]

    response = api_client.post(
        "/api/v1/datasets/releases",
        json={"dataset_snapshot_id": snapshot_id, "name": "empty-release", "version": "0.1.0"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "empty_dataset_snapshot"


def test_create_release_returns_422_for_invalid_ratios(api_client):
    sample_id = _create_sample(api_client, "S-RELEASE-RATIO")
    model_version_id = _create_model_version(api_client, "release-ratio-flow")
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
    analysis_run_id = run_response.json()["id"]
    api_client.post(f"/api/v1/analysis-runs/{analysis_run_id}/process")
    api_client.post(
        f"/api/v1/analysis-runs/{analysis_run_id}/reviews",
        json={"reviewer_name": "Dr. Vega", "review_decision": "confirmed"},
    )
    snapshot_response = api_client.post(
        "/api/v1/datasets/snapshots", json={"name": "ratio-snapshot", "version": "0.1.0"}
    )
    snapshot_id = snapshot_response.json()["id"]

    response = api_client.post(
        "/api/v1/datasets/releases",
        json={
            "dataset_snapshot_id": snapshot_id,
            "name": "bad-ratio-release",
            "version": "0.1.0",
            "train_ratio": 0.5,
            "validation_ratio": 0.3,
            "test_ratio": 0.3,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_split_ratios"
