from uuid import uuid4

from tests.api.test_annotation_quality_gates import _create_real_bundle
from tests.api.test_petri_region_reviews import _FORBIDDEN_TAXONOMY_WORDS

# "ultralytics_yolo" legitimately appears as the planned tool name in
# command_preview (it is never imported or executed) — only taxonomy and
# real deep-learning-framework terms are checked here.
_FORBIDDEN_DETECTION_WORDS = _FORBIDDEN_TAXONOMY_WORDS + ("torch", "pytorch", "tensorflow")


def _create_bundle_and_passed_gate(api_client, tmp_path, prefix="DT"):
    context, bundle = _create_real_bundle(api_client, tmp_path, prefix)
    gate_response = api_client.post(
        "/api/v1/ml/annotation-quality-gates",
        json={
            "annotation_bundle_run_id": bundle["id"],
            "config": {"fail_on_empty_split": False, "warn_on_single_class": False},
        },
    )
    assert gate_response.status_code == 201
    gate = gate_response.json()
    assert gate["status"] == "passed"
    return context, bundle, gate


def test_full_flow_create_and_query_detection_training_run(api_client, tmp_path):
    context, bundle, gate = _create_bundle_and_passed_gate(api_client, tmp_path, "DT-FULLFLOW")

    create_response = api_client.post(
        "/api/v1/ml/detection-training-runs",
        json={
            "annotation_bundle_run_id": bundle["id"],
            "annotation_quality_gate_run_id": gate["id"],
            "created_by": "qa",
        },
        headers={"X-Request-ID": "detection-training-request-1"},
    )

    assert create_response.status_code == 201
    assert create_response.headers["X-Request-ID"] == "detection-training-request-1"
    run = create_response.json()
    assert run["status"] == "planned"
    assert run["is_runnable"] is True
    assert run["command_preview"]["dry_run_only"] is True
    assert run["command_preview"]["tool"] == "ultralytics_yolo"
    assert "weights_path_planned" in run["expected_outputs"]

    detail_response = api_client.get(f"/api/v1/ml/detection-training-runs/{run['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == run["id"]

    issues_response = api_client.get(f"/api/v1/ml/detection-training-runs/{run['id']}/issues")
    assert issues_response.status_code == 200
    assert any(issue["code"] == "no_training_executed" for issue in issues_response.json()["issues"])

    by_release = api_client.get(f"/api/v1/datasets/releases/{context['release_id']}/detection-training-runs")
    assert by_release.status_code == 200
    assert [item["id"] for item in by_release.json()["detection_training_runs"]] == [run["id"]]

    by_bundle = api_client.get(f"/api/v1/ml/annotation-bundles/{bundle['id']}/detection-training-runs")
    assert by_bundle.status_code == 200
    assert [item["id"] for item in by_bundle.json()["detection_training_runs"]] == [run["id"]]

    by_gate = api_client.get(f"/api/v1/ml/annotation-quality-gates/{gate['id']}/detection-training-runs")
    assert by_gate.status_code == 200
    assert [item["id"] for item in by_gate.json()["detection_training_runs"]] == [run["id"]]

    list_response = api_client.get("/api/v1/ml/detection-training-runs")
    assert list_response.status_code == 200
    assert any(item["id"] == run["id"] for item in list_response.json()["detection_training_runs"])

    haystack = str(run).lower() + str(issues_response.json()).lower()
    for word in _FORBIDDEN_DETECTION_WORDS:
        assert word not in haystack


def test_status_planned_does_not_mean_trained_model(api_client, tmp_path):
    _, bundle, gate = _create_bundle_and_passed_gate(api_client, tmp_path, "DT-PLANNEDMEANING")

    create_response = api_client.post(
        "/api/v1/ml/detection-training-runs",
        json={"annotation_bundle_run_id": bundle["id"], "annotation_quality_gate_run_id": gate["id"]},
    )

    run = create_response.json()
    assert run["status"] == "planned"
    assert "weights_path_planned" in run["expected_outputs"]
    # A "planned" dry-run must not claim a real weights file exists on disk.
    assert run["expected_outputs"]["weights_path_planned"].endswith(".pt")


def test_create_detection_training_run_rejects_nonexistent_bundle(api_client):
    response = api_client.post(
        "/api/v1/ml/detection-training-runs",
        json={"annotation_bundle_run_id": str(uuid4()), "annotation_quality_gate_run_id": str(uuid4())},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "annotation_bundle_run_not_found"


def test_create_detection_training_run_rejects_nonexistent_quality_gate(api_client, tmp_path):
    _, bundle, _ = _create_bundle_and_passed_gate(api_client, tmp_path, "DT-NOGATE")

    response = api_client.post(
        "/api/v1/ml/detection-training-runs",
        json={"annotation_bundle_run_id": bundle["id"], "annotation_quality_gate_run_id": str(uuid4())},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "annotation_quality_gate_run_not_found"


def test_create_detection_training_run_rejects_quality_gate_from_other_bundle(api_client, tmp_path):
    _, bundle_a, gate_a = _create_bundle_and_passed_gate(api_client, tmp_path, "DT-CROSSA")
    _, bundle_b, _ = _create_bundle_and_passed_gate(api_client, tmp_path, "DT-CROSSB")

    response = api_client.post(
        "/api/v1/ml/detection-training-runs",
        json={"annotation_bundle_run_id": bundle_b["id"], "annotation_quality_gate_run_id": gate_a["id"]},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "detection_training_not_allowed"


def test_create_detection_training_run_blocks_on_dry_run_bundle(api_client):
    from tests.api.test_annotation_bundles import _create_export

    _, export_run = _create_export(api_client, "DT-DRYBUNDLE")
    bundle_response = api_client.post(
        "/api/v1/ml/annotation-bundles",
        json={"petri_annotation_export_run_id": export_run["id"], "config": {"dry_run": True}},
    )
    bundle = bundle_response.json()
    gate_response = api_client.post(
        "/api/v1/ml/annotation-quality-gates",
        json={"annotation_bundle_run_id": bundle["id"]},
    )
    gate = gate_response.json()
    assert gate["status"] == "failed"

    response = api_client.post(
        "/api/v1/ml/detection-training-runs",
        json={"annotation_bundle_run_id": bundle["id"], "annotation_quality_gate_run_id": gate["id"]},
    )

    assert response.status_code == 201
    run = response.json()
    assert run["status"] == "blocked"
    assert run["is_runnable"] is False


def test_create_detection_training_run_blocks_when_quality_gate_warning(api_client, tmp_path):
    context, bundle = _create_real_bundle(api_client, tmp_path, "DT-WARNGATE")
    gate_response = api_client.post(
        "/api/v1/ml/annotation-quality-gates",
        json={
            "annotation_bundle_run_id": bundle["id"],
            "config": {"fail_on_empty_split": False, "warn_on_single_class": True},
        },
    )
    gate = gate_response.json()
    assert gate["status"] == "warning"

    response = api_client.post(
        "/api/v1/ml/detection-training-runs",
        json={"annotation_bundle_run_id": bundle["id"], "annotation_quality_gate_run_id": gate["id"]},
    )

    assert response.status_code == 201
    run = response.json()
    assert run["status"] == "blocked"
    issues = api_client.get(f"/api/v1/ml/detection-training-runs/{run['id']}/issues").json()["issues"]
    assert any(issue["code"] == "quality_gate_not_passed" for issue in issues)


def test_create_detection_training_run_blocks_when_yolo_labels_missing(api_client, tmp_path):
    from tests.api.test_annotation_bundles import _create_export

    _, export_run = _create_export(api_client, "DT-NOLABELS")
    bundle_response = api_client.post(
        "/api/v1/ml/annotation-bundles",
        json={
            "petri_annotation_export_run_id": export_run["id"],
            "config": {"dry_run": False, "output_dir": str(tmp_path / "no-labels-bundle"), "include_yolo": False},
        },
    )
    bundle = bundle_response.json()
    gate_response = api_client.post(
        "/api/v1/ml/annotation-quality-gates",
        json={
            "annotation_bundle_run_id": bundle["id"],
            "config": {"fail_on_empty_split": False, "warn_on_single_class": False, "validate_yolo": False},
        },
    )
    gate = gate_response.json()
    assert gate["status"] == "passed"

    response = api_client.post(
        "/api/v1/ml/detection-training-runs",
        json={"annotation_bundle_run_id": bundle["id"], "annotation_quality_gate_run_id": gate["id"]},
    )

    assert response.status_code == 201
    run = response.json()
    assert run["status"] == "blocked"
    issues = api_client.get(f"/api/v1/ml/detection-training-runs/{run['id']}/issues").json()["issues"]
    assert any(issue["code"] == "yolo_labels_missing" for issue in issues)


def test_get_detection_training_run_returns_404_for_missing_run(api_client):
    response = api_client.get(f"/api/v1/ml/detection-training-runs/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "detection_training_run_not_found"


def test_list_issues_returns_404_for_missing_run(api_client):
    response = api_client.get(f"/api/v1/ml/detection-training-runs/{uuid4()}/issues")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "detection_training_run_not_found"
