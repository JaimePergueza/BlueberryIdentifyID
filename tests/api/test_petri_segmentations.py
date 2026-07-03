import os
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


def _create_release_with_audit(api_client, prefix: str) -> dict:
    sample_response = api_client.post("/api/v1/samples", json={"sample_code": prefix})
    assert sample_response.status_code == 201
    sample_id = sample_response.json()["id"]

    model_version_response = api_client.post(
        "/api/v1/model-versions",
        json={"name": f"petri-segmentation-{prefix}", "version": "0.1.0", "model_type": "mock"},
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
        json={"reviewer_name": "Dr. Segment", "review_decision": "confirmed"},
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


def test_full_flow_creates_petri_segmentation_run_and_regions(api_client):
    context = _create_release_with_audit(api_client, "PETRI-SEG-CREATE")

    response = api_client.post(
        "/api/v1/ml/petri-segmentations",
        json={"dataset_release_id": context["release_id"], "image_audit_run_id": context["audit_run_id"]},
        headers={"X-Request-ID": "petri-segmentation-request-1"},
    )

    assert response.status_code == 201
    assert response.headers["X-Request-ID"] == "petri-segmentation-request-1"
    body = response.json()
    assert body["status"] == "completed"
    assert body["processed_petri_images"] == 1
    assert body["total_regions_detected"] >= 1
    assert body["summary"]["processed_only_modality"] == "petri"
    assert body["summary"]["contains_taxonomy"] is False
    assert body["summary"]["contains_deep_learning"] is False
    assert body["regions"][0]["area_px"] > 1000


def test_get_list_filter_and_history_endpoints(api_client):
    context = _create_release_with_audit(api_client, "PETRI-SEG-LIST")
    create_response = api_client.post(
        "/api/v1/ml/petri-segmentations",
        json={"dataset_release_id": context["release_id"], "image_audit_run_id": context["audit_run_id"]},
    )
    run_id = create_response.json()["id"]
    split = create_response.json()["regions"][0]["split"]

    detail_response = api_client.get(f"/api/v1/ml/petri-segmentations/{run_id}")
    regions_response = api_client.get(f"/api/v1/ml/petri-segmentations/{run_id}/regions")
    filtered_response = api_client.get(f"/api/v1/ml/petri-segmentations/{run_id}/regions", params={"split": split})
    release_response = api_client.get(f"/api/v1/datasets/releases/{context['release_id']}/petri-segmentations")
    audit_response = api_client.get(f"/api/v1/ml/image-audits/{context['audit_run_id']}/petri-segmentations")
    list_response = api_client.get("/api/v1/ml/petri-segmentations")

    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == run_id
    assert regions_response.status_code == 200
    assert len(regions_response.json()) >= 1
    assert filtered_response.status_code == 200
    assert all(region["split"] == split for region in filtered_response.json())
    assert any(run["id"] == run_id for run in release_response.json())
    assert any(run["id"] == run_id for run in audit_response.json())
    assert any(run["id"] == run_id for run in list_response.json())


def test_petri_segmentation_response_has_no_taxonomy(api_client):
    context = _create_release_with_audit(api_client, "PETRI-SEG-NOTAXONOMY")
    create_response = api_client.post(
        "/api/v1/ml/petri-segmentations",
        json={"dataset_release_id": context["release_id"], "image_audit_run_id": context["audit_run_id"]},
    )
    run_id = create_response.json()["id"]

    detail_response = api_client.get(f"/api/v1/ml/petri-segmentations/{run_id}")
    regions_response = api_client.get(f"/api/v1/ml/petri-segmentations/{run_id}/regions")
    haystack = (str(create_response.json()) + str(detail_response.json()) + str(regions_response.json())).lower()

    for word in _FORBIDDEN_TAXONOMY_WORDS:
        assert word not in haystack
    assert "yolo" not in haystack
    assert "pytorch" not in haystack
    assert "tensorflow" not in haystack


def test_create_petri_segmentation_rejects_failed_audit(api_client):
    context = _create_release_with_audit(api_client, "PETRI-SEG-FAILEDAUDIT")
    os.remove(context["petri_image_path"])
    failed_audit_response = api_client.post(
        "/api/v1/ml/image-audits", json={"dataset_release_id": context["release_id"]}
    )
    assert failed_audit_response.status_code == 201
    assert failed_audit_response.json()["status"] == "failed"

    response = api_client.post(
        "/api/v1/ml/petri-segmentations",
        json={
            "dataset_release_id": context["release_id"],
            "image_audit_run_id": failed_audit_response.json()["id"],
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "petri_segmentation_not_allowed"


def test_create_petri_segmentation_rejects_audit_from_different_release(api_client):
    context_a = _create_release_with_audit(api_client, "PETRI-SEG-CROSSA")
    context_b = _create_release_with_audit(api_client, "PETRI-SEG-CROSSB")

    response = api_client.post(
        "/api/v1/ml/petri-segmentations",
        json={"dataset_release_id": context_a["release_id"], "image_audit_run_id": context_b["audit_run_id"]},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "petri_segmentation_not_allowed"
