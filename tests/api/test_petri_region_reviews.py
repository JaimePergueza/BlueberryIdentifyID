from io import BytesIO

from PIL import Image, ImageDraw

from tests.api.image_helpers import make_valid_png_bytes

_FORBIDDEN_TAXONOMY_WORDS = ("aspergillus", "penicillium", "botrytis", "escherichia", "salmonella")


def _make_detectable_petri_png() -> bytes:
    image = Image.new("RGB", (160, 160), "white")
    draw = ImageDraw.Draw(image)
    draw.ellipse((55, 55, 105, 105), fill="black")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _create_segmentation_run_with_region(api_client, prefix: str) -> dict:
    sample_response = api_client.post("/api/v1/samples", json={"sample_code": prefix})
    assert sample_response.status_code == 201
    sample_id = sample_response.json()["id"]

    model_version_response = api_client.post(
        "/api/v1/model-versions",
        json={"name": f"petri-region-review-{prefix}", "version": "0.1.0", "model_type": "mock"},
    )
    assert model_version_response.status_code == 201
    model_version_id = model_version_response.json()["id"]

    petri_response = api_client.post(
        f"/api/v1/samples/{sample_id}/petri-images",
        files={"file": ("petri.png", _make_detectable_petri_png(), "image/png")},
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
        json={"reviewer_name": "Dr. Region", "review_decision": "confirmed"},
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

    segmentation_response = api_client.post(
        "/api/v1/ml/petri-segmentations",
        json={"dataset_release_id": release_id, "image_audit_run_id": audit_run_id},
    )
    assert segmentation_response.status_code == 201
    segmentation_run_id = segmentation_response.json()["id"]
    region_id = segmentation_response.json()["regions"][0]["id"]

    return {
        "release_id": release_id,
        "segmentation_run_id": segmentation_run_id,
        "region_id": region_id,
    }


def test_full_flow_submit_and_query_petri_region_review(api_client):
    context = _create_segmentation_run_with_region(api_client, "PRR-FULLFLOW")

    submit_response = api_client.post(
        f"/api/v1/ml/petri-regions/{context['region_id']}/reviews",
        json={"decision": "candidate_valid", "reviewer_name": "Dr. Region", "confidence_score": 0.7},
        headers={"X-Request-ID": "petri-region-review-request-1"},
    )
    assert submit_response.status_code == 201
    assert submit_response.headers["X-Request-ID"] == "petri-region-review-request-1"
    review_id = submit_response.json()["id"]
    assert submit_response.json()["decision"] == "candidate_valid"
    assert submit_response.json()["is_final"] is True

    list_for_region = api_client.get(f"/api/v1/ml/petri-regions/{context['region_id']}/reviews")
    assert list_for_region.status_code == 200
    assert len(list_for_region.json()["reviews"]) == 1

    final_response = api_client.get(f"/api/v1/ml/petri-regions/{context['region_id']}/reviews/final")
    assert final_response.status_code == 200
    assert final_response.json()["id"] == review_id

    second_response = api_client.post(
        f"/api/v1/ml/petri-regions/{context['region_id']}/reviews",
        json={"decision": "candidate_false_positive", "reviewer_name": "Dr. Second"},
    )
    assert second_response.status_code == 201
    second_review_id = second_response.json()["id"]

    updated_final = api_client.get(f"/api/v1/ml/petri-regions/{context['region_id']}/reviews/final")
    assert updated_final.status_code == 200
    assert updated_final.json()["id"] == second_review_id

    list_for_run = api_client.get(f"/api/v1/ml/petri-segmentations/{context['segmentation_run_id']}/region-reviews")
    assert list_for_run.status_code == 200
    assert len(list_for_run.json()["reviews"]) == 2

    list_for_release = api_client.get(f"/api/v1/datasets/releases/{context['release_id']}/petri-region-reviews")
    assert list_for_release.status_code == 200
    assert len(list_for_release.json()["reviews"]) == 2

    manifest_response = api_client.get(
        f"/api/v1/ml/petri-segmentations/{context['segmentation_run_id']}/reviewed-annotations-manifest"
    )
    assert manifest_response.status_code == 200
    manifest = manifest_response.json()
    assert manifest["total_regions"] >= 1
    assert manifest["final_reviewed_regions"] == 1
    assert len(manifest["annotations"]) == 1
    assert manifest["annotations"][0]["decision"] == "candidate_false_positive"
    assert manifest["annotations"][0]["effective_bbox"] == manifest["annotations"][0]["original_bbox"]

    haystack = str(manifest).lower()
    for word in _FORBIDDEN_TAXONOMY_WORDS:
        assert word not in haystack
    assert "yolo" not in haystack


def test_corrected_bbox_becomes_effective_bbox_in_manifest(api_client):
    context = _create_segmentation_run_with_region(api_client, "PRR-CORRECTEDBBOX")

    api_client.post(
        f"/api/v1/ml/petri-regions/{context['region_id']}/reviews",
        json={
            "decision": "candidate_valid",
            "corrected_bbox_x": 3,
            "corrected_bbox_y": 4,
            "corrected_bbox_width": 40,
            "corrected_bbox_height": 42,
        },
    )

    manifest_response = api_client.get(
        f"/api/v1/ml/petri-segmentations/{context['segmentation_run_id']}/reviewed-annotations-manifest"
    )
    annotation = manifest_response.json()["annotations"][0]
    assert annotation["corrected_bbox"] == {"x": 3, "y": 4, "width": 40, "height": 42}
    assert annotation["effective_bbox"] == {"x": 3, "y": 4, "width": 40, "height": 42}


def test_petri_region_review_response_has_no_taxonomy(api_client):
    context = _create_segmentation_run_with_region(api_client, "PRR-NOTAXONOMY")

    submit_response = api_client.post(
        f"/api/v1/ml/petri-regions/{context['region_id']}/reviews",
        json={"decision": "candidate_uncertain"},
    )
    haystack = str(submit_response.json()).lower()
    for word in _FORBIDDEN_TAXONOMY_WORDS:
        assert word not in haystack
    assert "yolo" not in haystack
    assert "pytorch" not in haystack
    assert "tensorflow" not in haystack


def test_submit_review_for_nonexistent_region_returns_404(api_client):
    from uuid import uuid4

    response = api_client.post(
        f"/api/v1/ml/petri-regions/{uuid4()}/reviews",
        json={"decision": "candidate_valid"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "petri_segmentation_region_not_found"


def test_submit_review_rejects_invalid_confidence_score(api_client):
    context = _create_segmentation_run_with_region(api_client, "PRR-INVALIDCONF")

    response = api_client.post(
        f"/api/v1/ml/petri-regions/{context['region_id']}/reviews",
        json={"decision": "candidate_valid", "confidence_score": 1.5},
    )

    assert response.status_code == 422


def test_submit_review_rejects_invalid_bbox(api_client):
    context = _create_segmentation_run_with_region(api_client, "PRR-INVALIDBBOX")

    response = api_client.post(
        f"/api/v1/ml/petri-regions/{context['region_id']}/reviews",
        json={"decision": "candidate_valid", "corrected_bbox_width": 0, "corrected_bbox_height": 10},
    )

    assert response.status_code == 422


def test_get_final_review_returns_404_when_none_submitted(api_client):
    context = _create_segmentation_run_with_region(api_client, "PRR-NOFINAL")

    response = api_client.get(f"/api/v1/ml/petri-regions/{context['region_id']}/reviews/final")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "petri_region_review_not_found"


def test_list_reviews_for_nonexistent_segmentation_run_returns_404(api_client):
    from uuid import uuid4

    response = api_client.get(f"/api/v1/ml/petri-segmentations/{uuid4()}/region-reviews")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "petri_segmentation_run_not_found"


def test_list_reviews_for_nonexistent_dataset_release_returns_404(api_client):
    from uuid import uuid4

    response = api_client.get(f"/api/v1/datasets/releases/{uuid4()}/petri-region-reviews")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "dataset_release_not_found"
