from uuid import uuid4

from tests.api.test_annotation_quality_gates import _create_real_bundle
from tests.api.test_petri_region_reviews import _FORBIDDEN_TAXONOMY_WORDS

# torch/ultralytics/pytorch/tensorflow deliberately appear as config field
# names (e.g. "require_torch") documenting what is NOT required — only
# taxonomy terms are checked here.
_FORBIDDEN_ENV_WORDS = _FORBIDDEN_TAXONOMY_WORDS


def _create_bundle_and_passed_gate(api_client, tmp_path, prefix="DTE"):
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


def _create_planned_detection_training_run(api_client, bundle, gate):
    response = api_client.post(
        "/api/v1/ml/detection-training-runs",
        json={"annotation_bundle_run_id": bundle["id"], "annotation_quality_gate_run_id": gate["id"]},
    )
    assert response.status_code == 201
    run = response.json()
    assert run["status"] == "planned"
    return run


def _create_ready_readiness_report(api_client, run):
    response = api_client.post(
        "/api/v1/ml/detection-training-readiness-reports",
        json={"detection_training_run_id": run["id"], "config": {"require_minimum_data": False}},
    )
    assert response.status_code == 201
    report = response.json()
    assert report["decision"] == "ready_for_training"
    return report


def test_full_flow_create_and_query_environment_spec(api_client, tmp_path, monkeypatch):
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    context, bundle, gate = _create_bundle_and_passed_gate(api_client, tmp_path, "DTE-FULLFLOW")
    run = _create_planned_detection_training_run(api_client, bundle, gate)
    readiness = _create_ready_readiness_report(api_client, run)

    create_response = api_client.post(
        "/api/v1/ml/detection-training-environment-specs",
        json={
            "detection_training_run_id": run["id"],
            "readiness_report_id": readiness["id"],
            "config": {
                "allow_cpu_training": False,
                "artifact_output_dir": str(tmp_path),
                "pretrained_weights_policy": "not_applicable",
            },
            "created_by": "qa",
        },
        headers={"X-Request-ID": "environment-request-1"},
    )

    assert create_response.status_code == 201
    assert create_response.headers["X-Request-ID"] == "environment-request-1"
    spec = create_response.json()
    assert spec["decision"] == "environment_ready"
    assert spec["is_environment_ready"] is True
    assert spec["detection_training_run_id"] == run["id"]
    assert spec["readiness_report_id"] == readiness["id"]
    assert spec["annotation_bundle_run_id"] == bundle["id"]
    assert spec["dataset_release_id"] == context["release_id"]
    assert "detected_python_version" in spec["detected_environment"]
    assert "require_ultralytics" in spec["dependency_policy"]
    assert "require_gpu" in spec["hardware_policy"]
    assert "artifact_output_dir" in spec["artifact_policy"]
    assert "allow_ci_training" in spec["execution_policy"]

    detail_response = api_client.get(f"/api/v1/ml/detection-training-environment-specs/{spec['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == spec["id"]

    issues_response = api_client.get(f"/api/v1/ml/detection-training-environment-specs/{spec['id']}/issues")
    assert issues_response.status_code == 200
    assert any(issue["code"] == "no_training_executed" for issue in issues_response.json()["issues"])
    assert any(issue["code"] == "environment_check_safe_only" for issue in issues_response.json()["issues"])

    by_run = api_client.get(f"/api/v1/ml/detection-training-runs/{run['id']}/environment-specs")
    assert by_run.status_code == 200
    assert [item["id"] for item in by_run.json()["environment_specs"]] == [spec["id"]]

    by_readiness = api_client.get(
        f"/api/v1/ml/detection-training-readiness-reports/{readiness['id']}/environment-specs"
    )
    assert by_readiness.status_code == 200
    assert [item["id"] for item in by_readiness.json()["environment_specs"]] == [spec["id"]]

    by_bundle = api_client.get(
        f"/api/v1/ml/annotation-bundles/{bundle['id']}/detection-training-environment-specs"
    )
    assert by_bundle.status_code == 200
    assert [item["id"] for item in by_bundle.json()["environment_specs"]] == [spec["id"]]

    by_release = api_client.get(
        f"/api/v1/datasets/releases/{context['release_id']}/detection-training-environment-specs"
    )
    assert by_release.status_code == 200
    assert [item["id"] for item in by_release.json()["environment_specs"]] == [spec["id"]]

    list_response = api_client.get("/api/v1/ml/detection-training-environment-specs")
    assert list_response.status_code == 200
    assert any(item["id"] == spec["id"] for item in list_response.json()["environment_specs"])

    haystack = str(spec).lower() + str(issues_response.json()).lower()
    for word in _FORBIDDEN_ENV_WORDS:
        assert word not in haystack


def test_environment_spec_rejects_nonexistent_detection_training_run(api_client):
    response = api_client.post(
        "/api/v1/ml/detection-training-environment-specs",
        json={"detection_training_run_id": str(uuid4()), "readiness_report_id": str(uuid4())},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "detection_training_run_not_found"


def test_environment_spec_rejects_nonexistent_readiness_report(api_client, tmp_path):
    _, bundle, gate = _create_bundle_and_passed_gate(api_client, tmp_path, "DTE-NOREADINESS")
    run = _create_planned_detection_training_run(api_client, bundle, gate)

    response = api_client.post(
        "/api/v1/ml/detection-training-environment-specs",
        json={"detection_training_run_id": run["id"], "readiness_report_id": str(uuid4())},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "detection_training_readiness_report_not_found"


def test_environment_spec_rejects_readiness_report_from_other_run(api_client, tmp_path):
    _, bundle_a, gate_a = _create_bundle_and_passed_gate(api_client, tmp_path, "DTE-CROSSA")
    run_a = _create_planned_detection_training_run(api_client, bundle_a, gate_a)
    readiness_a = _create_ready_readiness_report(api_client, run_a)

    _, bundle_b, gate_b = _create_bundle_and_passed_gate(api_client, tmp_path, "DTE-CROSSB")
    run_b = _create_planned_detection_training_run(api_client, bundle_b, gate_b)

    response = api_client.post(
        "/api/v1/ml/detection-training-environment-specs",
        json={"detection_training_run_id": run_b["id"], "readiness_report_id": readiness_a["id"]},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "detection_training_environment_not_allowed"


def test_environment_spec_blocked_when_require_gpu(api_client, tmp_path):
    _, bundle, gate = _create_bundle_and_passed_gate(api_client, tmp_path, "DTE-GPU")
    run = _create_planned_detection_training_run(api_client, bundle, gate)
    readiness = _create_ready_readiness_report(api_client, run)

    response = api_client.post(
        "/api/v1/ml/detection-training-environment-specs",
        json={
            "detection_training_run_id": run["id"],
            "readiness_report_id": readiness["id"],
            "config": {"require_gpu": True},
        },
    )

    assert response.status_code == 201
    spec = response.json()
    assert spec["decision"] == "blocked_by_missing_requirements"
    assert spec["is_environment_ready"] is False
    issues = api_client.get(f"/api/v1/ml/detection-training-environment-specs/{spec['id']}/issues").json()["issues"]
    assert any(issue["code"] == "gpu_not_available" for issue in issues)


def test_get_environment_spec_returns_404_for_missing_spec(api_client):
    response = api_client.get(f"/api/v1/ml/detection-training-environment-specs/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "detection_training_environment_spec_not_found"


def test_list_environment_issues_returns_404_for_missing_spec(api_client):
    response = api_client.get(f"/api/v1/ml/detection-training-environment-specs/{uuid4()}/issues")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "detection_training_environment_spec_not_found"
