import os

from tests.api.image_helpers import make_valid_jpeg_bytes, make_valid_png_bytes

_FORBIDDEN_TAXONOMY_WORDS = ("aspergillus", "penicillium", "botrytis", "escherichia", "salmonella")


def _create_release(api_client, prefix: str) -> dict:
    """Full flow: Sample -> ModelVersion -> Petri/Micro upload -> AnalysisRun
    -> process -> final HumanReview -> DatasetSnapshot -> DatasetRelease."""
    sample_response = api_client.post("/api/v1/samples", json={"sample_code": prefix})
    assert sample_response.status_code == 201
    sample_id = sample_response.json()["id"]

    model_version_response = api_client.post(
        "/api/v1/model-versions",
        json={"name": f"image-audit-{prefix}", "version": "0.1.0", "model_type": "mock"},
    )
    assert model_version_response.status_code == 201
    model_version_id = model_version_response.json()["id"]

    petri_response = api_client.post(
        f"/api/v1/samples/{sample_id}/petri-images",
        files={"file": ("petri.jpg", make_valid_jpeg_bytes(), "image/jpeg")},
    )
    assert petri_response.status_code == 201
    petri_image_id = petri_response.json()["id"]

    micro_response = api_client.post(
        f"/api/v1/samples/{sample_id}/micro-images",
        files={"file": ("micro.png", make_valid_png_bytes(), "image/png")},
    )
    assert micro_response.status_code == 201
    micro_image_id = micro_response.json()["id"]

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
        json={"reviewer_name": "Dr. Ibarra", "review_decision": "confirmed"},
    )
    assert review_response.status_code == 201

    snapshot_response = api_client.post(
        "/api/v1/datasets/snapshots", json={"name": f"snapshot-{prefix}", "version": "0.1.0"}
    )
    assert snapshot_response.status_code == 201
    snapshot_id = snapshot_response.json()["id"]

    release_response = api_client.post(
        "/api/v1/datasets/releases",
        json={"dataset_snapshot_id": snapshot_id, "name": f"release-{prefix}", "version": "0.1.0"},
    )
    assert release_response.status_code == 201
    release_id = release_response.json()["id"]

    manifest_response = api_client.get(f"/api/v1/datasets/releases/{release_id}/manifest")
    assert manifest_response.status_code == 200
    manifest_item = manifest_response.json()["items"][0]

    return {
        "release_id": release_id,
        "sample_id": sample_id,
        "petri_image_path": manifest_item["petri_image_path"],
        "micro_image_path": manifest_item["micro_image_path"],
    }


def test_create_image_audit_run_with_default_config_flags_small_images_as_warning(api_client):
    context = _create_release(api_client, "IMGAUDIT-DEFAULT")

    response = api_client.post("/api/v1/ml/image-audits", json={"dataset_release_id": context["release_id"]})

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "warning"
    assert body["is_passed"] is True
    assert body["error_count"] == 0
    assert body["warning_count"] >= 1


def test_create_image_audit_run_with_lenient_config_passes(api_client):
    context = _create_release(api_client, "IMGAUDIT-LENIENT")

    response = api_client.post(
        "/api/v1/ml/image-audits",
        json={
            "dataset_release_id": context["release_id"],
            "image_audit_config": {"min_width": 1, "min_height": 1},
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "passed"
    assert body["is_passed"] is True
    assert body["error_count"] == 0
    assert body["warning_count"] == 0


def test_get_image_audit_run_returns_detail_with_issues(api_client):
    context = _create_release(api_client, "IMGAUDIT-GET")
    create_response = api_client.post("/api/v1/ml/image-audits", json={"dataset_release_id": context["release_id"]})
    audit_run_id = create_response.json()["id"]

    response = api_client.get(f"/api/v1/ml/image-audits/{audit_run_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == audit_run_id
    assert body["dataset_release_id"] == context["release_id"]
    assert len(body["issues"]) == body["warning_count"] + body["error_count"]


def test_list_image_audit_issues_for_run(api_client):
    context = _create_release(api_client, "IMGAUDIT-ISSUES")
    create_response = api_client.post("/api/v1/ml/image-audits", json={"dataset_release_id": context["release_id"]})
    audit_run_id = create_response.json()["id"]

    response = api_client.get(f"/api/v1/ml/image-audits/{audit_run_id}/issues")

    assert response.status_code == 200
    issues = response.json()
    assert len(issues) >= 1
    assert all(issue["audit_run_id"] == audit_run_id for issue in issues)
    assert all(issue["modality"] in {"petri", "micro"} for issue in issues)


def test_list_image_audits_for_dataset_release(api_client):
    context = _create_release(api_client, "IMGAUDIT-BYRELEASE")
    create_response = api_client.post("/api/v1/ml/image-audits", json={"dataset_release_id": context["release_id"]})
    assert create_response.status_code == 201

    response = api_client.get(f"/api/v1/datasets/releases/{context['release_id']}/image-audits")

    assert response.status_code == 200
    runs = response.json()
    assert len(runs) == 1
    assert runs[0]["dataset_release_id"] == context["release_id"]

    listing_response = api_client.get("/api/v1/ml/image-audits")
    assert listing_response.status_code == 200
    assert any(run["id"] == create_response.json()["id"] for run in listing_response.json())


def test_image_audit_summary_and_distributions_are_present(api_client):
    context = _create_release(api_client, "IMGAUDIT-SUMMARY")

    response = api_client.post("/api/v1/ml/image-audits", json={"dataset_release_id": context["release_id"]})

    body = response.json()
    assert "recommendations" in body["summary"]
    assert body["format_distribution"]
    assert body["color_mode_distribution"]
    assert body["dimension_distribution"]
    assert body["file_size_distribution"]


def test_image_audit_response_never_exposes_taxonomy_or_model_metrics(api_client):
    context = _create_release(api_client, "IMGAUDIT-TAXCHECK")
    create_response = api_client.post("/api/v1/ml/image-audits", json={"dataset_release_id": context["release_id"]})
    audit_run_id = create_response.json()["id"]

    detail_response = api_client.get(f"/api/v1/ml/image-audits/{audit_run_id}")
    issues_response = api_client.get(f"/api/v1/ml/image-audits/{audit_run_id}/issues")

    haystack = str(create_response.json()) + str(detail_response.json()) + str(issues_response.json())
    lowered = haystack.lower()
    for word in _FORBIDDEN_TAXONOMY_WORDS:
        assert word not in lowered
    for metric_word in ("accuracy", "precision", "recall", "f1_score"):
        assert metric_word not in lowered
    assert create_response.json()["summary"]["contains_model_metrics"] is False
    assert create_response.json()["summary"]["contains_taxonomy"] is False


def test_create_image_audit_run_preserves_x_request_id(api_client):
    context = _create_release(api_client, "IMGAUDIT-REQID")

    response = api_client.post(
        "/api/v1/ml/image-audits",
        json={"dataset_release_id": context["release_id"]},
        headers={"X-Request-ID": "image-audit-request-1"},
    )

    assert response.status_code == 201
    assert response.headers["X-Request-ID"] == "image-audit-request-1"


def test_create_image_audit_run_detects_missing_image_file(api_client):
    context = _create_release(api_client, "IMGAUDIT-MISSING")
    os.remove(context["petri_image_path"])

    response = api_client.post("/api/v1/ml/image-audits", json={"dataset_release_id": context["release_id"]})

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    assert body["is_passed"] is False
    assert any(issue["code"] == "image_missing" and issue["modality"] == "petri" for issue in body["issues"])
