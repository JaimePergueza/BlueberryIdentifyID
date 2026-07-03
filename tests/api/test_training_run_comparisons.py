from tests.api.test_training_runs import _create_preflight
from tests.api.test_ml_preflight import _create_release_with_all_splits

_FORBIDDEN_WORDS = (
    "pytorch",
    "tensorflow",
    "cnn",
    "vit",
    "aspergillus",
    "penicillium",
    "botrytis",
    "escherichia",
    "salmonella",
)


def _create_majority_run(api_client, release, preflight, experiment_name="comparison-majority-api"):
    response = api_client.post(
        "/api/v1/ml/training-runs/baseline",
        json={
            "dataset_release_id": release["id"],
            "preflight_run_id": preflight["id"],
            "experiment_name": experiment_name,
            "training_config": {
                "experiment_name": experiment_name,
                "output_dir": "out",
                "min_items_per_split": 1,
                "min_items_per_class": 1,
            },
            "baseline_model_type": "majority_class",
            "created_by": "qa",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_full_flow_creates_training_run_comparison_and_lists_entries(api_client):
    release = _create_release_with_all_splits(api_client)
    preflight = _create_preflight(api_client, release["id"])
    first_run = _create_majority_run(api_client, release, preflight, "comparison-majority-api-a")
    second_run = _create_majority_run(api_client, release, preflight, "comparison-majority-api-b")
    assert first_run["status"] == "completed"
    assert second_run["status"] == "completed"

    create_response = api_client.post(
        "/api/v1/ml/training-run-comparisons",
        json={
            "dataset_release_id": release["id"],
            "training_run_ids": [first_run["id"], second_run["id"]],
            "name": "phase-17-api-comparison",
            "primary_metric": "accuracy",
            "primary_split": "test",
            "selection_policy": "best_primary_metric",
            "created_by": "qa",
        },
        headers={"X-Request-ID": "comparison-request-1"},
    )

    assert create_response.status_code == 201
    assert create_response.headers["X-Request-ID"] == "comparison-request-1"
    comparison = create_response.json()
    assert comparison["dataset_release_id"] == release["id"]
    assert comparison["primary_metric"] == "accuracy"
    assert comparison["primary_split"] == "test"
    assert comparison["selection_policy"] == "best_primary_metric"
    assert comparison["selected_training_run_id"] in {first_run["id"], second_run["id"]}
    assert comparison["comparison_summary"]["contains_deep_learning"] is False
    assert comparison["comparison_summary"]["selection_is_preliminary"] is True
    assert len(comparison["entries"]) == 2
    assert [entry["rank"] for entry in comparison["entries"]] == [1, 2]
    assert all(entry["primary_metric_value"] is not None for entry in comparison["entries"])

    get_response = api_client.get(f"/api/v1/ml/training-run-comparisons/{comparison['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == comparison["id"]

    entries_response = api_client.get(f"/api/v1/ml/training-run-comparisons/{comparison['id']}/entries")
    assert entries_response.status_code == 200
    assert len(entries_response.json()) == 2

    list_response = api_client.get("/api/v1/ml/training-run-comparisons")
    assert list_response.status_code == 200
    assert any(item["id"] == comparison["id"] for item in list_response.json())

    release_history_response = api_client.get(
        f"/api/v1/datasets/releases/{release['id']}/training-run-comparisons"
    )
    assert release_history_response.status_code == 200
    assert any(item["id"] == comparison["id"] for item in release_history_response.json())

    haystack = str(comparison).lower() + str(entries_response.json()).lower()
    for word in _FORBIDDEN_WORDS:
        assert word not in haystack
