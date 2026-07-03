from tests.api.test_ml_preflight import _create_release_with_all_splits

_FORBIDDEN_TAXONOMY_WORDS = ("aspergillus", "penicillium", "botrytis", "escherichia", "salmonella")
_FORBIDDEN_TECH_WORDS = ("pytorch", "tensorflow", "cnn", "vit")


def _create_preflight(api_client, dataset_release_id: str) -> dict:
    response = api_client.post(
        "/api/v1/ml/preflight-runs",
        json={
            "dataset_release_id": dataset_release_id,
            "training_config": {
                "experiment_name": "baseline-api-preflight",
                "output_dir": "out",
                "min_items_per_split": 1,
                "min_items_per_class": 1,
            },
            "created_by": "qa",
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "passed"
    return response.json()


def _create_feature_extraction(api_client, dataset_release_id: str) -> dict:
    audit_response = api_client.post("/api/v1/ml/image-audits", json={"dataset_release_id": dataset_release_id})
    assert audit_response.status_code == 201
    assert audit_response.json()["status"] in {"passed", "warning"}
    extraction_response = api_client.post(
        "/api/v1/ml/image-feature-extractions",
        json={"dataset_release_id": dataset_release_id, "image_audit_run_id": audit_response.json()["id"]},
    )
    assert extraction_response.status_code == 201
    assert extraction_response.json()["status"] == "completed"
    return extraction_response.json()


def test_full_flow_creates_majority_class_training_run_and_predictions(api_client):
    release = _create_release_with_all_splits(api_client)
    preflight = _create_preflight(api_client, release["id"])

    create_response = api_client.post(
        "/api/v1/ml/training-runs/baseline",
        json={
            "dataset_release_id": release["id"],
            "preflight_run_id": preflight["id"],
            "experiment_name": "majority-baseline-api",
            "training_config": {
                "experiment_name": "majority-baseline-api",
                "output_dir": "out",
                "min_items_per_split": 1,
                "min_items_per_class": 1,
            },
            "baseline_model_type": "majority_class",
            "created_by": "qa",
            "notes": "no image tensor training",
        },
        headers={"X-Request-ID": "training-run-request-1"},
    )
    assert create_response.status_code == 201
    assert create_response.headers["X-Request-ID"] == "training-run-request-1"
    training_run = create_response.json()
    assert training_run["dataset_release_id"] == release["id"]
    assert training_run["preflight_run_id"] == preflight["id"]
    assert training_run["run_kind"] == "baseline"
    assert training_run["baseline_model_type"] == "majority_class"
    assert training_run["status"] == "completed"
    assert training_run["summary"]["uses_image_pixels"] is False
    assert training_run["baseline_state"]["majority_label"]
    assert "accuracy_overall" in training_run["metrics"]
    assert "confusion_matrix" in training_run["metrics"]
    assert "precision" not in training_run["metrics"]
    assert "recall" not in training_run["metrics"]
    assert "f1" not in training_run["metrics"]

    get_response = api_client.get(f"/api/v1/ml/training-runs/{training_run['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == training_run["id"]

    predictions_response = api_client.get(f"/api/v1/ml/training-runs/{training_run['id']}/predictions")
    assert predictions_response.status_code == 200
    predictions = predictions_response.json()
    assert len(predictions) == release["item_count"]
    assert {prediction["predicted_label"] for prediction in predictions} == {
        training_run["baseline_state"]["majority_label"]
    }

    train_predictions_response = api_client.get(
        f"/api/v1/ml/training-runs/{training_run['id']}/predictions",
        params={"split": "train"},
    )
    assert train_predictions_response.status_code == 200
    assert len(train_predictions_response.json()) == release["train_count"]
    assert all(prediction["split"] == "train" for prediction in train_predictions_response.json())

    list_response = api_client.get("/api/v1/ml/training-runs")
    assert list_response.status_code == 200
    assert any(item["id"] == training_run["id"] for item in list_response.json())

    release_history_response = api_client.get(f"/api/v1/datasets/releases/{release['id']}/training-runs")
    assert release_history_response.status_code == 200
    assert any(item["id"] == training_run["id"] for item in release_history_response.json())

    preflight_history_response = api_client.get(f"/api/v1/ml/preflight-runs/{preflight['id']}/training-runs")
    assert preflight_history_response.status_code == 200
    assert any(item["id"] == training_run["id"] for item in preflight_history_response.json())

    haystack = str(training_run) + str(predictions)
    for word in _FORBIDDEN_TAXONOMY_WORDS + _FORBIDDEN_TECH_WORDS:
        assert word not in haystack.lower()


def test_failed_preflight_cannot_start_baseline_training_run(api_client):
    release = _create_release_with_all_splits(api_client)
    failed_preflight_response = api_client.post(
        "/api/v1/ml/preflight-runs",
        json={
            "dataset_release_id": release["id"],
            "training_config": {
                "experiment_name": "baseline-api-failed-preflight",
                "output_dir": "out",
                "min_items_per_split": 2,
            },
        },
    )
    assert failed_preflight_response.status_code == 201
    failed_preflight = failed_preflight_response.json()
    assert failed_preflight["status"] == "failed"

    response = api_client.post(
        "/api/v1/ml/training-runs/baseline",
        json={
            "dataset_release_id": release["id"],
            "preflight_run_id": failed_preflight["id"],
            "experiment_name": "blocked-baseline",
            "training_config": {
                "experiment_name": "blocked-baseline",
                "output_dir": "out",
                "min_items_per_split": 1,
                "min_items_per_class": 1,
            },
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "baseline_training_not_allowed"


def test_full_flow_creates_classical_tabular_training_run_and_predictions(api_client):
    release = _create_release_with_all_splits(api_client)
    preflight = _create_preflight(api_client, release["id"])
    extraction = _create_feature_extraction(api_client, release["id"])

    create_response = api_client.post(
        "/api/v1/ml/training-runs/classical-baseline",
        json={
            "dataset_release_id": release["id"],
            "preflight_run_id": preflight["id"],
            "image_feature_extraction_run_id": extraction["id"],
            "experiment_name": "classical-baseline-api",
            "tabular_training_config": {
                "feature_extraction_run_id": extraction["id"],
                "model_type": "logistic_regression_tabular",
                "fusion_strategy": "concatenate",
                "min_train_items": 2,
                "min_classes_train": 2,
            },
            "created_by": "qa",
            "notes": "uses ImageFeatureVector only",
        },
        headers={"X-Request-ID": "classical-training-run-request-1"},
    )

    assert create_response.status_code == 201
    assert create_response.headers["X-Request-ID"] == "classical-training-run-request-1"
    training_run = create_response.json()
    assert training_run["baseline_model_type"] == "logistic_regression_tabular"
    assert training_run["status"] == "completed"
    assert training_run["summary"]["uses_image_pixels"] is False
    assert training_run["summary"]["contains_deep_learning"] is False
    assert training_run["baseline_state"]["feature_extraction_run_id"] == extraction["id"]
    assert training_run["summary"]["uses_image_feature_vectors"] is True
    assert training_run["baseline_state"]["feature_names"]
    assert "accuracy_overall" in training_run["metrics"]
    assert "confusion_matrix" in training_run["metrics"]
    assert "precision" not in training_run["metrics"]
    assert "recall" not in training_run["metrics"]
    assert "f1" not in training_run["metrics"]

    predictions_response = api_client.get(f"/api/v1/ml/training-runs/{training_run['id']}/predictions")
    assert predictions_response.status_code == 200
    assert len(predictions_response.json()) == release["item_count"]

    haystack = str(training_run).lower()
    for word in _FORBIDDEN_TAXONOMY_WORDS + _FORBIDDEN_TECH_WORDS:
        assert word not in haystack


def test_classical_baseline_rejects_failed_preflight(api_client):
    release = _create_release_with_all_splits(api_client)
    extraction = _create_feature_extraction(api_client, release["id"])
    failed_preflight_response = api_client.post(
        "/api/v1/ml/preflight-runs",
        json={
            "dataset_release_id": release["id"],
            "training_config": {
                "experiment_name": "classical-api-failed-preflight",
                "output_dir": "out",
                "min_items_per_split": 2,
            },
        },
    )
    assert failed_preflight_response.status_code == 201
    assert failed_preflight_response.json()["status"] == "failed"

    response = api_client.post(
        "/api/v1/ml/training-runs/classical-baseline",
        json={
            "dataset_release_id": release["id"],
            "preflight_run_id": failed_preflight_response.json()["id"],
            "image_feature_extraction_run_id": extraction["id"],
            "experiment_name": "blocked-classical",
            "tabular_training_config": {"feature_extraction_run_id": extraction["id"]},
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "baseline_training_not_allowed"
