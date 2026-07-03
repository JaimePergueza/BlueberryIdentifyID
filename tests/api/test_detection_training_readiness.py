from uuid import uuid4

from tests.api.test_annotation_quality_gates import _create_real_bundle
from tests.api.test_petri_region_reviews import _FORBIDDEN_TAXONOMY_WORDS

# torch/ultralytics/pytorch/tensorflow deliberately appear as config field
# names (e.g. "require_torch_installed") documenting what is NOT required —
# only taxonomy terms are checked here.
_FORBIDDEN_READINESS_WORDS = _FORBIDDEN_TAXONOMY_WORDS


def _create_bundle_and_passed_gate(api_client, tmp_path, prefix="DTR"):
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


def test_full_flow_creates_ready_readiness_report(api_client, tmp_path):
    context, bundle, gate = _create_bundle_and_passed_gate(api_client, tmp_path, "DTR-FULLFLOW")
    run = _create_planned_detection_training_run(api_client, bundle, gate)

    create_response = api_client.post(
        "/api/v1/ml/detection-training-readiness-reports",
        json={
            "detection_training_run_id": run["id"],
            "config": {"require_minimum_data": False},
            "created_by": "qa",
        },
        headers={"X-Request-ID": "readiness-request-1"},
    )

    assert create_response.status_code == 201
    assert create_response.headers["X-Request-ID"] == "readiness-request-1"
    report = create_response.json()
    assert report["decision"] == "ready_for_training"
    assert report["is_ready"] is True
    assert report["detection_training_run_id"] == run["id"]
    assert report["annotation_bundle_run_id"] == bundle["id"]
    assert report["annotation_quality_gate_run_id"] == gate["id"]
    assert report["dataset_release_id"] == context["release_id"]

    detail_response = api_client.get(f"/api/v1/ml/detection-training-readiness-reports/{report['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == report["id"]

    issues_response = api_client.get(f"/api/v1/ml/detection-training-readiness-reports/{report['id']}/issues")
    assert issues_response.status_code == 200
    assert any(issue["code"] == "no_training_executed" for issue in issues_response.json()["issues"])
    assert any(issue["code"] == "training_executor_missing" for issue in issues_response.json()["issues"])

    by_run = api_client.get(f"/api/v1/ml/detection-training-runs/{run['id']}/readiness-reports")
    assert by_run.status_code == 200
    assert [item["id"] for item in by_run.json()["readiness_reports"]] == [report["id"]]

    by_release = api_client.get(f"/api/v1/datasets/releases/{context['release_id']}/detection-training-readiness-reports")
    assert by_release.status_code == 200
    assert [item["id"] for item in by_release.json()["readiness_reports"]] == [report["id"]]

    by_bundle = api_client.get(f"/api/v1/ml/annotation-bundles/{bundle['id']}/detection-training-readiness-reports")
    assert by_bundle.status_code == 200
    assert [item["id"] for item in by_bundle.json()["readiness_reports"]] == [report["id"]]

    by_gate = api_client.get(
        f"/api/v1/ml/annotation-quality-gates/{gate['id']}/detection-training-readiness-reports"
    )
    assert by_gate.status_code == 200
    assert [item["id"] for item in by_gate.json()["readiness_reports"]] == [report["id"]]

    list_response = api_client.get("/api/v1/ml/detection-training-readiness-reports")
    assert list_response.status_code == 200
    assert any(item["id"] == report["id"] for item in list_response.json()["readiness_reports"])

    haystack = str(report).lower() + str(issues_response.json()).lower()
    for word in _FORBIDDEN_READINESS_WORDS:
        assert word not in haystack


def test_readiness_report_needs_more_annotations_by_default(api_client, tmp_path):
    _, bundle, gate = _create_bundle_and_passed_gate(api_client, tmp_path, "DTR-MOREDATA")
    run = _create_planned_detection_training_run(api_client, bundle, gate)

    response = api_client.post(
        "/api/v1/ml/detection-training-readiness-reports",
        json={"detection_training_run_id": run["id"]},
    )

    assert response.status_code == 201
    report = response.json()
    assert report["decision"] == "needs_more_annotations"
    assert report["status"] == "blocked"
    assert report["is_ready"] is False


def test_readiness_report_rejects_nonexistent_detection_training_run(api_client):
    response = api_client.post(
        "/api/v1/ml/detection-training-readiness-reports",
        json={"detection_training_run_id": str(uuid4())},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "detection_training_run_not_found"


def test_readiness_report_blocked_detection_training_run(api_client, tmp_path):
    from tests.api.test_annotation_bundles import _create_export

    _, export_run = _create_export(api_client, "DTR-BLOCKEDRUN")
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
    run_response = api_client.post(
        "/api/v1/ml/detection-training-runs",
        json={"annotation_bundle_run_id": bundle["id"], "annotation_quality_gate_run_id": gate["id"]},
    )
    run = run_response.json()
    assert run["status"] == "blocked"

    response = api_client.post(
        "/api/v1/ml/detection-training-readiness-reports",
        json={"detection_training_run_id": run["id"]},
    )

    assert response.status_code == 201
    report = response.json()
    assert report["decision"] == "blocked_by_contract"
    assert report["is_ready"] is False
    issues = api_client.get(f"/api/v1/ml/detection-training-readiness-reports/{report['id']}/issues").json()["issues"]
    assert any(issue["code"] == "detection_training_not_planned" for issue in issues)


def test_readiness_report_failed_quality_gate(api_client, tmp_path):
    context, bundle = _create_real_bundle(api_client, tmp_path, "DTR-WARNGATE")
    gate_response = api_client.post(
        "/api/v1/ml/annotation-quality-gates",
        json={
            "annotation_bundle_run_id": bundle["id"],
            "config": {"fail_on_empty_split": False, "warn_on_single_class": True},
        },
    )
    gate = gate_response.json()
    assert gate["status"] == "warning"
    run_response = api_client.post(
        "/api/v1/ml/detection-training-runs",
        json={"annotation_bundle_run_id": bundle["id"], "annotation_quality_gate_run_id": gate["id"]},
    )
    run = run_response.json()
    assert run["status"] == "blocked"

    response = api_client.post(
        "/api/v1/ml/detection-training-readiness-reports",
        json={"detection_training_run_id": run["id"]},
    )

    assert response.status_code == 201
    report = response.json()
    assert report["decision"] == "blocked_by_contract"


def test_readiness_report_blocked_by_environment_when_ultralytics_required(api_client, tmp_path):
    _, bundle, gate = _create_bundle_and_passed_gate(api_client, tmp_path, "DTR-ULTRA")
    run = _create_planned_detection_training_run(api_client, bundle, gate)

    response = api_client.post(
        "/api/v1/ml/detection-training-readiness-reports",
        json={
            "detection_training_run_id": run["id"],
            "config": {"require_minimum_data": False, "require_ultralytics_installed": True},
        },
    )

    assert response.status_code == 201
    report = response.json()
    assert report["decision"] == "blocked_by_environment"
    assert report["is_ready"] is False
    issues = api_client.get(f"/api/v1/ml/detection-training-readiness-reports/{report['id']}/issues").json()["issues"]
    assert any(issue["code"] == "ultralytics_not_installed" for issue in issues)


def test_get_readiness_report_returns_404_for_missing_report(api_client):
    response = api_client.get(f"/api/v1/ml/detection-training-readiness-reports/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "detection_training_readiness_report_not_found"


def test_list_readiness_issues_returns_404_for_missing_report(api_client):
    response = api_client.get(f"/api/v1/ml/detection-training-readiness-reports/{uuid4()}/issues")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "detection_training_readiness_report_not_found"
