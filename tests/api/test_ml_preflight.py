from tests.api.image_helpers import make_valid_jpeg_bytes, make_valid_png_bytes

_FORBIDDEN_TAXONOMY_WORDS = ("aspergillus", "penicillium", "botrytis", "escherichia", "salmonella")
_FORBIDDEN_METRIC_WORDS = ("accuracy", "precision", "recall", "f1", "confusion_matrix")


def _create_sample(api_client, sample_code: str) -> str:
    response = api_client.post(
        "/api/v1/samples",
        json={"sample_code": sample_code, "lot_code": f"LOT-{sample_code}", "origin": "farm-a"},
    )
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


def _create_reviewed_run(api_client, sample_code: str, model_version_id: str, corrected_label: str) -> str:
    sample_id = _create_sample(api_client, sample_code)
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
    review_response = api_client.post(
        f"/api/v1/analysis-runs/{analysis_run_id}/reviews",
        json={
            "reviewer_name": "Dr. Preflight",
            "review_decision": "corrected",
            "corrected_label": corrected_label,
        },
    )
    assert review_response.status_code == 201
    return analysis_run_id


def _create_release_with_all_splits(api_client) -> dict:
    model_version_id = _create_model_version(api_client, "preflight-flow")
    labels = [
        "suspicious_growth",
        "no_evident_growth",
        "suspicious_growth",
        "probable_fungal_growth",
    ]
    for index, label in enumerate(labels):
        _create_reviewed_run(api_client, f"S-PREFLIGHT-{index}", model_version_id, label)

    snapshot_response = api_client.post(
        "/api/v1/datasets/snapshots",
        json={"name": "preflight-snapshot", "version": "0.1.0", "created_by": "qa"},
    )
    assert snapshot_response.status_code == 201
    snapshot = snapshot_response.json()
    assert snapshot["item_count"] == 4

    release_response = api_client.post(
        "/api/v1/datasets/releases",
        json={
            "dataset_snapshot_id": snapshot["id"],
            "name": "preflight-release",
            "version": "0.1.0",
            "random_seed": 7,
            "train_ratio": 0.5,
            "validation_ratio": 0.25,
            "test_ratio": 0.25,
            "created_by": "qa",
        },
    )
    assert release_response.status_code == 201
    release = release_response.json()
    assert release["train_count"] == 2
    assert release["validation_count"] == 1
    assert release["test_count"] == 1
    return release


def test_full_flow_creates_training_preflight_run_and_lists_history(api_client):
    release = _create_release_with_all_splits(api_client)

    create_response = api_client.post(
        "/api/v1/ml/preflight-runs",
        json={
            "dataset_release_id": release["id"],
            "training_config": {
                "experiment_name": "preflight-api",
                "output_dir": "out",
                "min_items_per_split": 1,
                "min_items_per_class": 1,
            },
            "created_by": "qa",
            "notes": "persistent validation only",
        },
        headers={"X-Request-ID": "preflight-request-1"},
    )
    assert create_response.status_code == 201
    assert create_response.headers["X-Request-ID"] == "preflight-request-1"
    preflight = create_response.json()
    assert preflight["dataset_release_id"] == release["id"]
    assert preflight["status"] == "passed"
    assert preflight["is_valid"] is True
    assert preflight["config"]["experiment_name"] == "preflight-api"
    assert preflight["item_count"] == 4
    assert preflight["train_count"] == 2
    assert preflight["validation_count"] == 1
    assert preflight["test_count"] == 1
    assert preflight["issues"] == []

    get_response = api_client.get(f"/api/v1/ml/preflight-runs/{preflight['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == preflight["id"]

    issues_response = api_client.get(f"/api/v1/ml/preflight-runs/{preflight['id']}/issues")
    assert issues_response.status_code == 200
    assert issues_response.json() == []

    release_history_response = api_client.get(f"/api/v1/datasets/releases/{release['id']}/preflight-runs")
    assert release_history_response.status_code == 200
    assert any(item["id"] == preflight["id"] for item in release_history_response.json())

    list_response = api_client.get("/api/v1/ml/preflight-runs")
    assert list_response.status_code == 200
    assert any(item["id"] == preflight["id"] for item in list_response.json())

    haystack = str(preflight) + str(get_response.json()) + str(release_history_response.json())
    for word in _FORBIDDEN_TAXONOMY_WORDS + _FORBIDDEN_METRIC_WORDS:
        assert word not in haystack.lower()


def test_preflight_invalid_manifest_is_persisted_as_failed_with_issues(api_client):
    release = _create_release_with_all_splits(api_client)

    response = api_client.post(
        "/api/v1/ml/preflight-runs",
        json={
            "dataset_release_id": release["id"],
            "training_config": {
                "experiment_name": "preflight-api-invalid",
                "output_dir": "out",
                "min_items_per_split": 2,
            },
        },
    )

    assert response.status_code == 201
    preflight = response.json()
    assert preflight["status"] == "failed"
    assert preflight["is_valid"] is False
    assert any(issue["severity"] == "error" for issue in preflight["issues"])
