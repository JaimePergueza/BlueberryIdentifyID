from tests.api.test_petri_annotation_exports import _create_valid_review
from tests.api.test_petri_region_reviews import _FORBIDDEN_TAXONOMY_WORDS, _create_segmentation_run_with_region


def _create_export(api_client, prefix="AB"):
    context = _create_segmentation_run_with_region(api_client, prefix)
    _create_valid_review(api_client, context, corrected=True)
    response = api_client.post(
        "/api/v1/ml/petri-annotation-exports",
        json={
            "dataset_release_id": context["release_id"],
            "petri_segmentation_run_id": context["segmentation_run_id"],
            "config": {"export_format": "blueberry_manifest"},
        },
    )
    assert response.status_code == 201
    return context, response.json()


def test_full_flow_create_annotation_bundle_dry_run(api_client):
    context, export_run = _create_export(api_client, "AB-DRY")

    create_response = api_client.post(
        "/api/v1/ml/annotation-bundles",
        json={
            "petri_annotation_export_run_id": export_run["id"],
            "config": {"dry_run": True, "output_dir": "not-written"},
            "created_by": "qa",
        },
        headers={"X-Request-ID": "annotation-bundle-request-1"},
    )

    assert create_response.status_code == 201
    assert create_response.headers["X-Request-ID"] == "annotation-bundle-request-1"
    bundle = create_response.json()
    assert bundle["status"] == "dry_run"
    assert bundle["annotation_count"] == 1
    assert bundle["image_count"] == 1
    assert bundle["label_count"] == 1
    assert bundle["bundle_manifest"]["contains_training"] is False
    assert bundle["bundle_manifest"]["contains_taxonomy"] is False

    detail_response = api_client.get(f"/api/v1/ml/annotation-bundles/{bundle['id']}")
    assert detail_response.status_code == 200

    files_response = api_client.get(f"/api/v1/ml/annotation-bundles/{bundle['id']}/files")
    assert files_response.status_code == 200
    relative_paths = {file["relative_path"] for file in files_response.json()["files"]}
    assert relative_paths >= {
        "README.md",
        "annotations/blueberry_manifest.json",
        "annotations/coco_annotations.json",
        "dataset.yaml",
        "manifest.json",
    }
    assert any(path.startswith("annotations/yolo/") and path.endswith(".txt") for path in relative_paths)

    by_release = api_client.get(f"/api/v1/datasets/releases/{context['release_id']}/annotation-bundles")
    assert by_release.status_code == 200
    assert [item["id"] for item in by_release.json()["bundles"]] == [bundle["id"]]

    by_export = api_client.get(f"/api/v1/ml/petri-annotation-exports/{export_run['id']}/annotation-bundles")
    assert by_export.status_code == 200
    assert [item["id"] for item in by_export.json()["bundles"]] == [bundle["id"]]

    haystack = str(bundle).lower() + str(files_response.json()).lower()
    for word in _FORBIDDEN_TAXONOMY_WORDS:
        assert word not in haystack
    assert "pytorch" not in haystack
    assert "tensorflow" not in haystack


def test_creates_real_annotation_bundle_without_copying_images(api_client, tmp_path):
    _, export_run = _create_export(api_client, "AB-REAL")
    output_dir = tmp_path / "bundle"

    response = api_client.post(
        "/api/v1/ml/annotation-bundles",
        json={
            "petri_annotation_export_run_id": export_run["id"],
            "config": {"dry_run": False, "output_dir": str(output_dir)},
        },
    )

    assert response.status_code == 201
    bundle = response.json()
    assert bundle["status"] == "completed"
    assert (output_dir / "manifest.json").exists()
    assert not (output_dir / "images").exists()
    assert bundle["bundle_manifest"]["copy_images"] is False


def test_rejects_copy_images_and_missing_export(api_client):
    _, export_run = _create_export(api_client, "AB-REJECT")

    copy_response = api_client.post(
        "/api/v1/ml/annotation-bundles",
        json={"petri_annotation_export_run_id": export_run["id"], "config": {"copy_images": True}},
    )
    assert copy_response.status_code == 409
    assert copy_response.json()["error"]["code"] == "annotation_bundle_not_allowed"

    missing_response = api_client.get("/api/v1/ml/annotation-bundles/00000000-0000-0000-0000-000000000000")
    assert missing_response.status_code == 404
    assert missing_response.json()["error"]["code"] == "annotation_bundle_run_not_found"
