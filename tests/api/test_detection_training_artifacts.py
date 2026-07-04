from uuid import uuid4

from tests.api.test_detection_training_environment import (
    _create_bundle_and_passed_gate,
    _create_planned_detection_training_run,
    _create_ready_readiness_report,
)
from tests.api.test_petri_region_reviews import _FORBIDDEN_TAXONOMY_WORDS

_FORBIDDEN_ARTIFACT_WORDS = _FORBIDDEN_TAXONOMY_WORDS


def _create_ready_environment_spec(api_client, run, readiness, tmp_path, prefix="env"):
    output_dir = tmp_path / prefix
    output_dir.mkdir(parents=True, exist_ok=True)
    response = api_client.post(
        "/api/v1/ml/detection-training-environment-specs",
        json={
            "detection_training_run_id": run["id"],
            "readiness_report_id": readiness["id"],
            "config": {
                "allow_cpu_training": False,
                "artifact_output_dir": str(output_dir),
                "pretrained_weights_policy": "not_applicable",
            },
        },
    )
    assert response.status_code == 201
    spec = response.json()
    assert spec["decision"] == "environment_ready"
    return spec


def test_full_flow_create_and_query_artifact_policy(api_client, tmp_path, monkeypatch):
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    context, bundle, gate = _create_bundle_and_passed_gate(api_client, tmp_path, "DTA-FULLFLOW")
    run = _create_planned_detection_training_run(api_client, bundle, gate)
    readiness = _create_ready_readiness_report(api_client, run)
    environment_spec = _create_ready_environment_spec(api_client, run, readiness, tmp_path, "DTA-FULLFLOW-env")

    artifact_root = tmp_path / "DTA-FULLFLOW-artifacts"

    create_response = api_client.post(
        "/api/v1/ml/detection-training-artifact-policies",
        json={
            "detection_training_run_id": run["id"],
            "readiness_report_id": readiness["id"],
            "environment_spec_id": environment_spec["id"],
            "config": {"artifact_root_dir": str(artifact_root), "require_gitignore_rules": False},
            "created_by": "qa",
        },
        headers={"X-Request-ID": "artifact-request-1"},
    )

    assert create_response.status_code == 201
    assert create_response.headers["X-Request-ID"] == "artifact-request-1"
    policy = create_response.json()
    assert policy["decision"] == "artifact_policy_ready"
    assert policy["is_policy_ready"] is True
    assert policy["detection_training_run_id"] == run["id"]
    assert policy["readiness_report_id"] == readiness["id"]
    assert policy["environment_spec_id"] == environment_spec["id"]
    assert policy["annotation_bundle_run_id"] == bundle["id"]
    assert policy["dataset_release_id"] == context["release_id"]
    assert "artifact_root_dir" in policy["storage_policy"]
    assert "gitignore_modified" in policy["git_policy"]
    assert policy["git_policy"]["gitignore_modified"] is False
    assert "checksums_computed" in policy["checksum_policy"]
    assert policy["checksum_policy"]["checksums_computed"] is False
    assert "planned_record_count" in policy["registry_summary"]
    assert policy["registry_summary"]["actual_record_count"] == 0

    detail_response = api_client.get(f"/api/v1/ml/detection-training-artifact-policies/{policy['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == policy["id"]

    records_response = api_client.get(f"/api/v1/ml/detection-training-artifact-policies/{policy['id']}/records")
    assert records_response.status_code == 200
    records = records_response.json()["records"]
    assert len(records) == 4
    assert {record["artifact_kind"] for record in records} == {
        "planned_weights",
        "planned_metrics",
        "planned_predictions",
        "planned_run_dir",
    }
    for record in records:
        assert record["artifact_state"] == "planned"
        assert record["checksum_sha256"] is None

    issues_response = api_client.get(f"/api/v1/ml/detection-training-artifact-policies/{policy['id']}/issues")
    assert issues_response.status_code == 200
    issues = issues_response.json()["issues"]
    assert any(issue["code"] == "no_training_executed" for issue in issues)
    assert any(issue["code"] == "planned_artifact_only" for issue in issues)

    by_run = api_client.get(f"/api/v1/ml/detection-training-runs/{run['id']}/artifact-policies")
    assert by_run.status_code == 200
    assert [item["id"] for item in by_run.json()["artifact_policies"]] == [policy["id"]]

    by_readiness = api_client.get(
        f"/api/v1/ml/detection-training-readiness-reports/{readiness['id']}/artifact-policies"
    )
    assert by_readiness.status_code == 200
    assert [item["id"] for item in by_readiness.json()["artifact_policies"]] == [policy["id"]]

    by_environment = api_client.get(
        f"/api/v1/ml/detection-training-environment-specs/{environment_spec['id']}/artifact-policies"
    )
    assert by_environment.status_code == 200
    assert [item["id"] for item in by_environment.json()["artifact_policies"]] == [policy["id"]]

    by_bundle = api_client.get(
        f"/api/v1/ml/annotation-bundles/{bundle['id']}/detection-training-artifact-policies"
    )
    assert by_bundle.status_code == 200
    assert [item["id"] for item in by_bundle.json()["artifact_policies"]] == [policy["id"]]

    by_release = api_client.get(
        f"/api/v1/datasets/releases/{context['release_id']}/detection-training-artifact-policies"
    )
    assert by_release.status_code == 200
    assert [item["id"] for item in by_release.json()["artifact_policies"]] == [policy["id"]]

    list_response = api_client.get("/api/v1/ml/detection-training-artifact-policies")
    assert list_response.status_code == 200
    assert any(item["id"] == policy["id"] for item in list_response.json()["artifact_policies"])

    haystack = (
        str(policy).lower()
        + str(records_response.json()).lower()
        + str(issues_response.json()).lower()
    )
    for word in _FORBIDDEN_ARTIFACT_WORDS:
        assert word not in haystack


def test_artifact_policy_rejects_nonexistent_detection_training_run(api_client):
    response = api_client.post(
        "/api/v1/ml/detection-training-artifact-policies",
        json={
            "detection_training_run_id": str(uuid4()),
            "readiness_report_id": str(uuid4()),
            "environment_spec_id": str(uuid4()),
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "detection_training_run_not_found"


def test_artifact_policy_rejects_nonexistent_readiness_report(api_client, tmp_path):
    _, bundle, gate = _create_bundle_and_passed_gate(api_client, tmp_path, "DTA-NOREADINESS")
    run = _create_planned_detection_training_run(api_client, bundle, gate)

    response = api_client.post(
        "/api/v1/ml/detection-training-artifact-policies",
        json={
            "detection_training_run_id": run["id"],
            "readiness_report_id": str(uuid4()),
            "environment_spec_id": str(uuid4()),
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "detection_training_readiness_report_not_found"


def test_artifact_policy_rejects_nonexistent_environment_spec(api_client, tmp_path):
    _, bundle, gate = _create_bundle_and_passed_gate(api_client, tmp_path, "DTA-NOENV")
    run = _create_planned_detection_training_run(api_client, bundle, gate)
    readiness = _create_ready_readiness_report(api_client, run)

    response = api_client.post(
        "/api/v1/ml/detection-training-artifact-policies",
        json={
            "detection_training_run_id": run["id"],
            "readiness_report_id": readiness["id"],
            "environment_spec_id": str(uuid4()),
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "detection_training_environment_spec_not_found"


def test_artifact_policy_rejects_readiness_report_from_other_run(api_client, tmp_path, monkeypatch):
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    _, bundle_a, gate_a = _create_bundle_and_passed_gate(api_client, tmp_path, "DTA-CROSSA")
    run_a = _create_planned_detection_training_run(api_client, bundle_a, gate_a)
    readiness_a = _create_ready_readiness_report(api_client, run_a)
    environment_a = _create_ready_environment_spec(api_client, run_a, readiness_a, tmp_path, "DTA-CROSSA-env")

    _, bundle_b, gate_b = _create_bundle_and_passed_gate(api_client, tmp_path, "DTA-CROSSB")
    run_b = _create_planned_detection_training_run(api_client, bundle_b, gate_b)

    response = api_client.post(
        "/api/v1/ml/detection-training-artifact-policies",
        json={
            "detection_training_run_id": run_b["id"],
            "readiness_report_id": readiness_a["id"],
            "environment_spec_id": environment_a["id"],
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "detection_training_artifact_policy_not_allowed"


def test_artifact_policy_rejects_environment_spec_from_other_run(api_client, tmp_path, monkeypatch):
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    _, bundle_a, gate_a = _create_bundle_and_passed_gate(api_client, tmp_path, "DTA-ENVOTHERRUNA")
    run_a = _create_planned_detection_training_run(api_client, bundle_a, gate_a)
    readiness_a = _create_ready_readiness_report(api_client, run_a)
    environment_a = _create_ready_environment_spec(api_client, run_a, readiness_a, tmp_path, "DTA-ENVOTHERRUNA-env")

    _, bundle_b, gate_b = _create_bundle_and_passed_gate(api_client, tmp_path, "DTA-ENVOTHERRUNB")
    run_b = _create_planned_detection_training_run(api_client, bundle_b, gate_b)
    readiness_b = _create_ready_readiness_report(api_client, run_b)

    response = api_client.post(
        "/api/v1/ml/detection-training-artifact-policies",
        json={
            "detection_training_run_id": run_b["id"],
            "readiness_report_id": readiness_b["id"],
            "environment_spec_id": environment_a["id"],
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "detection_training_artifact_policy_not_allowed"


def test_artifact_policy_rejects_environment_spec_from_other_readiness_report(api_client, tmp_path, monkeypatch):
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    _, bundle, gate = _create_bundle_and_passed_gate(api_client, tmp_path, "DTA-ENVOTHERREADINESS")
    run = _create_planned_detection_training_run(api_client, bundle, gate)
    readiness = _create_ready_readiness_report(api_client, run)
    environment_spec = _create_ready_environment_spec(api_client, run, readiness, tmp_path, "DTA-ENVOTHERREADINESS-env")

    other_readiness_response = api_client.post(
        "/api/v1/ml/detection-training-readiness-reports",
        json={"detection_training_run_id": run["id"], "config": {"require_minimum_data": False}},
    )
    assert other_readiness_response.status_code == 201
    other_readiness = other_readiness_response.json()

    response = api_client.post(
        "/api/v1/ml/detection-training-artifact-policies",
        json={
            "detection_training_run_id": run["id"],
            "readiness_report_id": other_readiness["id"],
            "environment_spec_id": environment_spec["id"],
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "detection_training_artifact_policy_not_allowed"


def test_artifact_policy_blocked_when_root_dir_inside_repo(api_client, tmp_path, monkeypatch):
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    _, bundle, gate = _create_bundle_and_passed_gate(api_client, tmp_path, "DTA-INSIDEREPO")
    run = _create_planned_detection_training_run(api_client, bundle, gate)
    readiness = _create_ready_readiness_report(api_client, run)
    environment_spec = _create_ready_environment_spec(api_client, run, readiness, tmp_path, "DTA-INSIDEREPO-env")

    response = api_client.post(
        "/api/v1/ml/detection-training-artifact-policies",
        json={
            "detection_training_run_id": run["id"],
            "readiness_report_id": readiness["id"],
            "environment_spec_id": environment_spec["id"],
            "config": {"artifact_root_dir": ".", "allow_artifacts_inside_repo": False},
        },
    )

    assert response.status_code == 201
    policy = response.json()
    assert policy["decision"] == "blocked_by_repo_storage"
    assert policy["is_policy_ready"] is False
    issues = api_client.get(f"/api/v1/ml/detection-training-artifact-policies/{policy['id']}/issues").json()[
        "issues"
    ]
    assert any(issue["code"] == "output_dir_inside_repo" for issue in issues)


def test_artifact_policy_blocked_when_root_dir_missing(api_client, tmp_path, monkeypatch):
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    _, bundle, gate = _create_bundle_and_passed_gate(api_client, tmp_path, "DTA-MISSINGROOT")
    run = _create_planned_detection_training_run(api_client, bundle, gate)
    readiness = _create_ready_readiness_report(api_client, run)
    environment_spec = _create_ready_environment_spec(api_client, run, readiness, tmp_path, "DTA-MISSINGROOT-env")

    response = api_client.post(
        "/api/v1/ml/detection-training-artifact-policies",
        json={
            "detection_training_run_id": run["id"],
            "readiness_report_id": readiness["id"],
            "environment_spec_id": environment_spec["id"],
            "config": {"require_artifact_root_dir": True},
        },
    )

    assert response.status_code == 201
    policy = response.json()
    assert policy["decision"] == "blocked_by_missing_output_dir"
    assert policy["is_policy_ready"] is False
    issues = api_client.get(f"/api/v1/ml/detection-training-artifact-policies/{policy['id']}/issues").json()[
        "issues"
    ]
    assert any(issue["code"] == "output_dir_missing" for issue in issues)


def test_get_artifact_policy_returns_404_for_missing_policy(api_client):
    response = api_client.get(f"/api/v1/ml/detection-training-artifact-policies/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "detection_training_artifact_policy_not_found"


def test_list_artifact_records_returns_404_for_missing_policy(api_client):
    response = api_client.get(f"/api/v1/ml/detection-training-artifact-policies/{uuid4()}/records")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "detection_training_artifact_policy_not_found"


def test_list_artifact_issues_returns_404_for_missing_policy(api_client):
    response = api_client.get(f"/api/v1/ml/detection-training-artifact-policies/{uuid4()}/issues")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "detection_training_artifact_policy_not_found"
