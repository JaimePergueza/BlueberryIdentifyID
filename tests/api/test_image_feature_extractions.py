import os

from tests.api.image_helpers import make_valid_jpeg_bytes, make_valid_png_bytes

_FORBIDDEN_TAXONOMY_WORDS = ("aspergillus", "penicillium", "botrytis", "escherichia", "salmonella")
_FORBIDDEN_METRIC_WORDS = ("accuracy", "precision", "recall", "f1_score", "confusion_matrix")


def _create_release_with_audit(api_client, prefix: str) -> dict:
    """Full flow: Sample -> ModelVersion -> Petri/Micro upload -> AnalysisRun
    -> process -> final HumanReview -> DatasetSnapshot -> DatasetRelease ->
    ImageDatasetAuditRun."""
    sample_response = api_client.post("/api/v1/samples", json={"sample_code": prefix})
    assert sample_response.status_code == 201
    sample_id = sample_response.json()["id"]

    model_version_response = api_client.post(
        "/api/v1/model-versions",
        json={"name": f"feature-extraction-{prefix}", "version": "0.1.0", "model_type": "mock"},
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

    audit_response = api_client.post("/api/v1/ml/image-audits", json={"dataset_release_id": release_id})
    assert audit_response.status_code == 201
    audit_run_id = audit_response.json()["id"]
    assert audit_response.json()["status"] in {"passed", "warning"}

    manifest_response = api_client.get(f"/api/v1/datasets/releases/{release_id}/manifest")
    assert manifest_response.status_code == 200
    manifest_item = manifest_response.json()["items"][0]

    return {
        "release_id": release_id,
        "audit_run_id": audit_run_id,
        "petri_image_path": manifest_item["petri_image_path"],
    }


def test_create_feature_extraction_run_completed(api_client):
    context = _create_release_with_audit(api_client, "FEAT-CREATE")

    response = api_client.post(
        "/api/v1/ml/image-feature-extractions",
        json={"dataset_release_id": context["release_id"], "image_audit_run_id": context["audit_run_id"]},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["is_completed"] is True
    assert body["total_feature_vectors"] == 2
    assert body["petri_feature_count"] == 1
    assert body["micro_feature_count"] == 1
    assert "geometry" in body["vectors"][0]["features"]


def test_get_feature_extraction_run_returns_vectors(api_client):
    context = _create_release_with_audit(api_client, "FEAT-GET")
    create_response = api_client.post(
        "/api/v1/ml/image-feature-extractions",
        json={"dataset_release_id": context["release_id"], "image_audit_run_id": context["audit_run_id"]},
    )
    run_id = create_response.json()["id"]

    response = api_client.get(f"/api/v1/ml/image-feature-extractions/{run_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == run_id
    assert len(body["vectors"]) == 2


def test_list_feature_vectors_for_run(api_client):
    context = _create_release_with_audit(api_client, "FEAT-VECTORS")
    create_response = api_client.post(
        "/api/v1/ml/image-feature-extractions",
        json={"dataset_release_id": context["release_id"], "image_audit_run_id": context["audit_run_id"]},
    )
    run_id = create_response.json()["id"]

    response = api_client.get(f"/api/v1/ml/image-feature-extractions/{run_id}/vectors")

    assert response.status_code == 200
    vectors = response.json()
    assert len(vectors) == 2


def test_filter_vectors_by_modality(api_client):
    context = _create_release_with_audit(api_client, "FEAT-MODALITY")
    create_response = api_client.post(
        "/api/v1/ml/image-feature-extractions",
        json={"dataset_release_id": context["release_id"], "image_audit_run_id": context["audit_run_id"]},
    )
    run_id = create_response.json()["id"]

    response = api_client.get(f"/api/v1/ml/image-feature-extractions/{run_id}/vectors", params={"modality": "petri"})

    assert response.status_code == 200
    vectors = response.json()
    assert len(vectors) == 1
    assert vectors[0]["modality"] == "petri"


def test_filter_vectors_by_split(api_client):
    context = _create_release_with_audit(api_client, "FEAT-SPLIT")
    create_response = api_client.post(
        "/api/v1/ml/image-feature-extractions",
        json={"dataset_release_id": context["release_id"], "image_audit_run_id": context["audit_run_id"]},
    )
    run_id = create_response.json()["id"]
    expected_split = create_response.json()["vectors"][0]["split"]

    response = api_client.get(
        f"/api/v1/ml/image-feature-extractions/{run_id}/vectors", params={"split": expected_split}
    )

    assert response.status_code == 200
    vectors = response.json()
    assert len(vectors) == 2
    assert all(v["split"] == expected_split for v in vectors)


def test_list_extractions_by_dataset_release(api_client):
    context = _create_release_with_audit(api_client, "FEAT-BYRELEASE")
    create_response = api_client.post(
        "/api/v1/ml/image-feature-extractions",
        json={"dataset_release_id": context["release_id"], "image_audit_run_id": context["audit_run_id"]},
    )
    assert create_response.status_code == 201

    response = api_client.get(f"/api/v1/datasets/releases/{context['release_id']}/image-feature-extractions")

    assert response.status_code == 200
    runs = response.json()
    assert len(runs) == 1
    assert runs[0]["dataset_release_id"] == context["release_id"]


def test_list_extractions_by_image_audit_run(api_client):
    context = _create_release_with_audit(api_client, "FEAT-BYAUDIT")
    create_response = api_client.post(
        "/api/v1/ml/image-feature-extractions",
        json={"dataset_release_id": context["release_id"], "image_audit_run_id": context["audit_run_id"]},
    )
    assert create_response.status_code == 201

    response = api_client.get(f"/api/v1/ml/image-audits/{context['audit_run_id']}/feature-extractions")

    assert response.status_code == 200
    runs = response.json()
    assert len(runs) == 1
    assert runs[0]["image_audit_run_id"] == context["audit_run_id"]

    listing_response = api_client.get("/api/v1/ml/image-feature-extractions")
    assert listing_response.status_code == 200
    assert any(run["id"] == create_response.json()["id"] for run in listing_response.json())


def test_feature_extraction_response_has_no_classification_metrics_or_taxonomy(api_client):
    context = _create_release_with_audit(api_client, "FEAT-NOTAXONOMY")
    create_response = api_client.post(
        "/api/v1/ml/image-feature-extractions",
        json={"dataset_release_id": context["release_id"], "image_audit_run_id": context["audit_run_id"]},
    )
    run_id = create_response.json()["id"]

    detail_response = api_client.get(f"/api/v1/ml/image-feature-extractions/{run_id}")
    vectors_response = api_client.get(f"/api/v1/ml/image-feature-extractions/{run_id}/vectors")

    haystack = (str(create_response.json()) + str(detail_response.json()) + str(vectors_response.json())).lower()
    for word in _FORBIDDEN_TAXONOMY_WORDS:
        assert word not in haystack
    for word in _FORBIDDEN_METRIC_WORDS:
        assert word not in haystack
    assert create_response.json()["summary"]["contains_model_metrics"] is False
    assert create_response.json()["summary"]["contains_taxonomy"] is False


def test_create_feature_extraction_run_preserves_x_request_id(api_client):
    context = _create_release_with_audit(api_client, "FEAT-REQID")

    response = api_client.post(
        "/api/v1/ml/image-feature-extractions",
        json={"dataset_release_id": context["release_id"], "image_audit_run_id": context["audit_run_id"]},
        headers={"X-Request-ID": "feature-extraction-request-1"},
    )

    assert response.status_code == 201
    assert response.headers["X-Request-ID"] == "feature-extraction-request-1"


def test_create_feature_extraction_run_rejects_failed_audit(api_client):
    context = _create_release_with_audit(api_client, "FEAT-FAILEDAUDIT")
    os.remove(context["petri_image_path"])

    failed_audit_response = api_client.post(
        "/api/v1/ml/image-audits", json={"dataset_release_id": context["release_id"]}
    )
    assert failed_audit_response.status_code == 201
    assert failed_audit_response.json()["status"] == "failed"
    failed_audit_run_id = failed_audit_response.json()["id"]

    response = api_client.post(
        "/api/v1/ml/image-feature-extractions",
        json={"dataset_release_id": context["release_id"], "image_audit_run_id": failed_audit_run_id},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "image_feature_extraction_not_allowed"


def test_create_feature_extraction_run_rejects_audit_from_different_release(api_client):
    context_a = _create_release_with_audit(api_client, "FEAT-CROSSA")
    context_b = _create_release_with_audit(api_client, "FEAT-CROSSB")

    response = api_client.post(
        "/api/v1/ml/image-feature-extractions",
        json={"dataset_release_id": context_a["release_id"], "image_audit_run_id": context_b["audit_run_id"]},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "image_feature_extraction_not_allowed"
