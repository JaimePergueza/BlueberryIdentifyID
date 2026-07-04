from uuid import uuid4

from tests.api.test_detection_training_artifacts import _create_ready_environment_spec
from tests.api.test_detection_training_environment import (
    _create_bundle_and_passed_gate,
    _create_planned_detection_training_run,
    _create_ready_readiness_report,
)
from tests.api.test_petri_region_reviews import _FORBIDDEN_TAXONOMY_WORDS

_FORBIDDEN_EXECUTION_WORDS = _FORBIDDEN_TAXONOMY_WORDS
_REQUIRED_CONFIRMATION_TEXT = "I understand this will only create a scaffold and will not train a model"


def _create_ready_artifact_policy(api_client, run, readiness, environment_spec, tmp_path, prefix="artifacts"):
    artifact_root = tmp_path / prefix
    response = api_client.post(
        "/api/v1/ml/detection-training-artifact-policies",
        json={
            "detection_training_run_id": run["id"],
            "readiness_report_id": readiness["id"],
            "environment_spec_id": environment_spec["id"],
            "config": {"artifact_root_dir": str(artifact_root), "require_gitignore_rules": False},
        },
    )
    assert response.status_code == 201
    policy = response.json()
    assert policy["decision"] == "artifact_policy_ready"
    return policy


def _build_full_chain(api_client, tmp_path, monkeypatch, prefix):
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    context, bundle, gate = _create_bundle_and_passed_gate(api_client, tmp_path, prefix)
    run = _create_planned_detection_training_run(api_client, bundle, gate)
    readiness = _create_ready_readiness_report(api_client, run)
    environment_spec = _create_ready_environment_spec(api_client, run, readiness, tmp_path, f"{prefix}-env")
    artifact_policy = _create_ready_artifact_policy(
        api_client, run, readiness, environment_spec, tmp_path, f"{prefix}-artifacts"
    )
    return context, bundle, gate, run, readiness, environment_spec, artifact_policy


def test_full_flow_create_and_query_execution_run(api_client, tmp_path, monkeypatch):
    context, bundle, gate, run, readiness, environment_spec, artifact_policy = _build_full_chain(
        api_client, tmp_path, monkeypatch, "DTX-FULLFLOW"
    )

    create_response = api_client.post(
        "/api/v1/ml/detection-training-execution-runs",
        json={
            "detection_training_run_id": run["id"],
            "readiness_report_id": readiness["id"],
            "environment_spec_id": environment_spec["id"],
            "artifact_policy_id": artifact_policy["id"],
            "config": {
                "manual_confirmation_text": _REQUIRED_CONFIRMATION_TEXT,
                "allow_ready_to_execute_status": True,
            },
            "created_by": "qa",
        },
        headers={"X-Request-ID": "execution-request-1"},
    )

    assert create_response.status_code == 201
    assert create_response.headers["X-Request-ID"] == "execution-request-1"
    execution_run = create_response.json()
    assert execution_run["status"] == "ready_to_execute"
    assert execution_run["decision"] == "ready_for_manual_execution"
    assert execution_run["is_executable"] is False
    assert execution_run["detection_training_run_id"] == run["id"]
    assert execution_run["readiness_report_id"] == readiness["id"]
    assert execution_run["environment_spec_id"] == environment_spec["id"]
    assert execution_run["artifact_policy_id"] == artifact_policy["id"]
    assert execution_run["annotation_bundle_run_id"] == bundle["id"]
    assert execution_run["dataset_release_id"] == context["release_id"]
    assert "manual_steps" in execution_run["execution_plan"]
    assert "prohibited_actions" in execution_run["execution_plan"]
    assert "command_preview" in execution_run["execution_plan"]

    detail_response = api_client.get(f"/api/v1/ml/detection-training-execution-runs/{execution_run['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == execution_run["id"]

    issues_response = api_client.get(f"/api/v1/ml/detection-training-execution-runs/{execution_run['id']}/issues")
    assert issues_response.status_code == 200
    issues = issues_response.json()["issues"]
    assert any(issue["code"] == "no_training_executed" for issue in issues)
    assert any(issue["code"] == "real_runner_not_implemented" for issue in issues)

    by_run = api_client.get(f"/api/v1/ml/detection-training-runs/{run['id']}/execution-runs")
    assert by_run.status_code == 200
    assert [item["id"] for item in by_run.json()["execution_runs"]] == [execution_run["id"]]

    by_readiness = api_client.get(
        f"/api/v1/ml/detection-training-readiness-reports/{readiness['id']}/execution-runs"
    )
    assert by_readiness.status_code == 200
    assert [item["id"] for item in by_readiness.json()["execution_runs"]] == [execution_run["id"]]

    by_environment = api_client.get(
        f"/api/v1/ml/detection-training-environment-specs/{environment_spec['id']}/execution-runs"
    )
    assert by_environment.status_code == 200
    assert [item["id"] for item in by_environment.json()["execution_runs"]] == [execution_run["id"]]

    by_artifact_policy = api_client.get(
        f"/api/v1/ml/detection-training-artifact-policies/{artifact_policy['id']}/execution-runs"
    )
    assert by_artifact_policy.status_code == 200
    assert [item["id"] for item in by_artifact_policy.json()["execution_runs"]] == [execution_run["id"]]

    by_bundle = api_client.get(
        f"/api/v1/ml/annotation-bundles/{bundle['id']}/detection-training-execution-runs"
    )
    assert by_bundle.status_code == 200
    assert [item["id"] for item in by_bundle.json()["execution_runs"]] == [execution_run["id"]]

    by_release = api_client.get(
        f"/api/v1/datasets/releases/{context['release_id']}/detection-training-execution-runs"
    )
    assert by_release.status_code == 200
    assert [item["id"] for item in by_release.json()["execution_runs"]] == [execution_run["id"]]

    list_response = api_client.get("/api/v1/ml/detection-training-execution-runs")
    assert list_response.status_code == 200
    assert any(item["id"] == execution_run["id"] for item in list_response.json()["execution_runs"])

    haystack = (
        str(execution_run).lower() + str(issues_response.json()).lower()
    )
    for word in _FORBIDDEN_EXECUTION_WORDS:
        assert word not in haystack


def test_execution_run_manual_required_without_confirmation(api_client, tmp_path, monkeypatch):
    context, bundle, gate, run, readiness, environment_spec, artifact_policy = _build_full_chain(
        api_client, tmp_path, monkeypatch, "DTX-MANUAL"
    )

    response = api_client.post(
        "/api/v1/ml/detection-training-execution-runs",
        json={
            "detection_training_run_id": run["id"],
            "readiness_report_id": readiness["id"],
            "environment_spec_id": environment_spec["id"],
            "artifact_policy_id": artifact_policy["id"],
        },
    )

    assert response.status_code == 201
    execution_run = response.json()
    assert execution_run["status"] == "manual_required"
    assert execution_run["decision"] == "manual_confirmation_required"


def test_execution_run_blocked_when_enable_real_training_true(api_client, tmp_path, monkeypatch):
    context, bundle, gate, run, readiness, environment_spec, artifact_policy = _build_full_chain(
        api_client, tmp_path, monkeypatch, "DTX-REALTRAINING"
    )

    response = api_client.post(
        "/api/v1/ml/detection-training-execution-runs",
        json={
            "detection_training_run_id": run["id"],
            "readiness_report_id": readiness["id"],
            "environment_spec_id": environment_spec["id"],
            "artifact_policy_id": artifact_policy["id"],
            "config": {"enable_real_training": True},
        },
    )

    assert response.status_code == 201
    execution_run = response.json()
    assert execution_run["status"] == "blocked"
    issues = api_client.get(
        f"/api/v1/ml/detection-training-execution-runs/{execution_run['id']}/issues"
    ).json()["issues"]
    assert any(issue["code"] == "training_execution_disabled" for issue in issues)


def test_execution_run_rejects_nonexistent_detection_training_run(api_client):
    response = api_client.post(
        "/api/v1/ml/detection-training-execution-runs",
        json={
            "detection_training_run_id": str(uuid4()),
            "readiness_report_id": str(uuid4()),
            "environment_spec_id": str(uuid4()),
            "artifact_policy_id": str(uuid4()),
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "detection_training_run_not_found"


def test_execution_run_rejects_nonexistent_readiness_report(api_client, tmp_path, monkeypatch):
    context, bundle, gate, run, readiness, environment_spec, artifact_policy = _build_full_chain(
        api_client, tmp_path, monkeypatch, "DTX-NOREADINESS"
    )

    response = api_client.post(
        "/api/v1/ml/detection-training-execution-runs",
        json={
            "detection_training_run_id": run["id"],
            "readiness_report_id": str(uuid4()),
            "environment_spec_id": environment_spec["id"],
            "artifact_policy_id": artifact_policy["id"],
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "detection_training_readiness_report_not_found"


def test_execution_run_rejects_nonexistent_environment_spec(api_client, tmp_path, monkeypatch):
    context, bundle, gate, run, readiness, environment_spec, artifact_policy = _build_full_chain(
        api_client, tmp_path, monkeypatch, "DTX-NOENV"
    )

    response = api_client.post(
        "/api/v1/ml/detection-training-execution-runs",
        json={
            "detection_training_run_id": run["id"],
            "readiness_report_id": readiness["id"],
            "environment_spec_id": str(uuid4()),
            "artifact_policy_id": artifact_policy["id"],
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "detection_training_environment_spec_not_found"


def test_execution_run_rejects_nonexistent_artifact_policy(api_client, tmp_path, monkeypatch):
    context, bundle, gate, run, readiness, environment_spec, artifact_policy = _build_full_chain(
        api_client, tmp_path, monkeypatch, "DTX-NOPOLICY"
    )

    response = api_client.post(
        "/api/v1/ml/detection-training-execution-runs",
        json={
            "detection_training_run_id": run["id"],
            "readiness_report_id": readiness["id"],
            "environment_spec_id": environment_spec["id"],
            "artifact_policy_id": str(uuid4()),
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "detection_training_artifact_policy_not_found"


def test_execution_run_rejects_readiness_report_from_other_run(api_client, tmp_path, monkeypatch):
    context_a, bundle_a, gate_a, run_a, readiness_a, environment_a, artifact_a = _build_full_chain(
        api_client, tmp_path, monkeypatch, "DTX-CROSSA"
    )
    context_b, bundle_b, gate_b, run_b, readiness_b, environment_b, artifact_b = _build_full_chain(
        api_client, tmp_path, monkeypatch, "DTX-CROSSB"
    )

    response = api_client.post(
        "/api/v1/ml/detection-training-execution-runs",
        json={
            "detection_training_run_id": run_b["id"],
            "readiness_report_id": readiness_a["id"],
            "environment_spec_id": environment_b["id"],
            "artifact_policy_id": artifact_b["id"],
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "detection_training_execution_run_not_allowed"


def test_execution_run_rejects_environment_spec_from_other_readiness_report(api_client, tmp_path, monkeypatch):
    context, bundle, gate, run, readiness, environment_spec, artifact_policy = _build_full_chain(
        api_client, tmp_path, monkeypatch, "DTX-CROSSENV"
    )
    other_readiness_response = api_client.post(
        "/api/v1/ml/detection-training-readiness-reports",
        json={"detection_training_run_id": run["id"], "config": {"require_minimum_data": False}},
    )
    assert other_readiness_response.status_code == 201
    other_readiness = other_readiness_response.json()

    response = api_client.post(
        "/api/v1/ml/detection-training-execution-runs",
        json={
            "detection_training_run_id": run["id"],
            "readiness_report_id": other_readiness["id"],
            "environment_spec_id": environment_spec["id"],
            "artifact_policy_id": artifact_policy["id"],
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "detection_training_execution_run_not_allowed"


def test_execution_run_rejects_artifact_policy_from_other_environment_spec(api_client, tmp_path, monkeypatch):
    context, bundle, gate, run, readiness, environment_spec, artifact_policy = _build_full_chain(
        api_client, tmp_path, monkeypatch, "DTX-CROSSARTIFACT"
    )
    other_environment_spec = _create_ready_environment_spec(
        api_client, run, readiness, tmp_path, "DTX-CROSSARTIFACT-env2"
    )
    other_artifact_policy = _create_ready_artifact_policy(
        api_client, run, readiness, other_environment_spec, tmp_path, "DTX-CROSSARTIFACT-artifacts2"
    )

    response = api_client.post(
        "/api/v1/ml/detection-training-execution-runs",
        json={
            "detection_training_run_id": run["id"],
            "readiness_report_id": readiness["id"],
            "environment_spec_id": environment_spec["id"],
            "artifact_policy_id": other_artifact_policy["id"],
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "detection_training_execution_run_not_allowed"


def test_get_execution_run_returns_404_for_missing_run(api_client):
    response = api_client.get(f"/api/v1/ml/detection-training-execution-runs/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "detection_training_execution_run_not_found"


def test_list_execution_issues_returns_404_for_missing_run(api_client):
    response = api_client.get(f"/api/v1/ml/detection-training-execution-runs/{uuid4()}/issues")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "detection_training_execution_run_not_found"
