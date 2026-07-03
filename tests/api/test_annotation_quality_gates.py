from tests.api.test_annotation_bundles import _create_export
from tests.api.test_petri_region_reviews import _FORBIDDEN_TAXONOMY_WORDS


def _create_real_bundle(api_client, tmp_path, prefix="AQG"):
    context, export_run = _create_export(api_client, prefix)
    output_dir = tmp_path / f"bundle-{prefix}"
    response = api_client.post(
        "/api/v1/ml/annotation-bundles",
        json={
            "petri_annotation_export_run_id": export_run["id"],
            "config": {"dry_run": False, "output_dir": str(output_dir)},
        },
    )
    assert response.status_code == 201
    return context, response.json()


def test_full_flow_create_annotation_quality_gate(api_client, tmp_path):
    context, bundle = _create_real_bundle(api_client, tmp_path, "AQG-PASS")

    create_response = api_client.post(
        "/api/v1/ml/annotation-quality-gates",
        json={
            "annotation_bundle_run_id": bundle["id"],
            "config": {"fail_on_empty_split": False, "warn_on_single_class": False},
            "created_by": "qa",
        },
        headers={"X-Request-ID": "annotation-quality-gate-request-1"},
    )

    assert create_response.status_code == 201
    assert create_response.headers["X-Request-ID"] == "annotation-quality-gate-request-1"
    gate = create_response.json()
    assert gate["status"] == "passed"
    assert gate["is_passed"] is True
    assert gate["total_images"] == 1
    assert gate["total_annotations"] == 1
    assert sum(split["annotations"] for split in gate["split_distribution"].values()) == 1
    assert gate["category_distribution"] == {"candidate_region": 1}

    detail_response = api_client.get(f"/api/v1/ml/annotation-quality-gates/{gate['id']}")
    assert detail_response.status_code == 200

    issues_response = api_client.get(f"/api/v1/ml/annotation-quality-gates/{gate['id']}/issues")
    assert issues_response.status_code == 200
    assert issues_response.json()["issues"] == []

    by_release = api_client.get(f"/api/v1/datasets/releases/{context['release_id']}/annotation-quality-gates")
    assert by_release.status_code == 200
    assert [item["id"] for item in by_release.json()["quality_gates"]] == [gate["id"]]

    by_bundle = api_client.get(f"/api/v1/ml/annotation-bundles/{bundle['id']}/quality-gates")
    assert by_bundle.status_code == 200
    assert [item["id"] for item in by_bundle.json()["quality_gates"]] == [gate["id"]]

    haystack = str(gate).lower() + str(issues_response.json()).lower()
    for word in _FORBIDDEN_TAXONOMY_WORDS:
        assert word not in haystack
    assert "pytorch" not in haystack
    assert "tensorflow" not in haystack


def test_quality_gate_persists_failed_status_for_dry_run_bundle(api_client):
    _, export_run = _create_export(api_client, "AQG-DRY")
    bundle_response = api_client.post(
        "/api/v1/ml/annotation-bundles",
        json={"petri_annotation_export_run_id": export_run["id"], "config": {"dry_run": True}},
    )
    assert bundle_response.status_code == 201
    bundle = bundle_response.json()

    gate_response = api_client.post(
        "/api/v1/ml/annotation-quality-gates",
        json={"annotation_bundle_run_id": bundle["id"]},
    )

    assert gate_response.status_code == 201
    gate = gate_response.json()
    assert gate["status"] == "failed"
    assert gate["is_passed"] is False
    issues = api_client.get(f"/api/v1/ml/annotation-quality-gates/{gate['id']}/issues").json()["issues"]
    assert any(issue["code"] == "bundle_not_completed" for issue in issues)


def test_quality_gate_returns_404_for_missing_bundle_and_gate(api_client):
    missing_bundle = api_client.post(
        "/api/v1/ml/annotation-quality-gates",
        json={"annotation_bundle_run_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert missing_bundle.status_code == 404
    assert missing_bundle.json()["error"]["code"] == "annotation_bundle_run_not_found"

    missing_gate = api_client.get("/api/v1/ml/annotation-quality-gates/00000000-0000-0000-0000-000000000000")
    assert missing_gate.status_code == 404
    assert missing_gate.json()["error"]["code"] == "annotation_quality_gate_run_not_found"
