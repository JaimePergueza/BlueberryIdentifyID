from tests.api.test_petri_region_reviews import _FORBIDDEN_TAXONOMY_WORDS, _create_segmentation_run_with_region


def _create_valid_review(api_client, context, *, corrected=False):
    payload = {"decision": "candidate_valid", "reviewer_name": "Dr. Export"}
    if corrected:
        payload.update(
            {
                "corrected_bbox_x": 5,
                "corrected_bbox_y": 6,
                "corrected_bbox_width": 30,
                "corrected_bbox_height": 32,
            }
        )
    response = api_client.post(f"/api/v1/ml/petri-regions/{context['region_id']}/reviews", json=payload)
    assert response.status_code == 201
    return response.json()


def test_full_flow_create_blueberry_annotation_export(api_client):
    context = _create_segmentation_run_with_region(api_client, "PAE-BLUEBERRY")
    _create_valid_review(api_client, context, corrected=True)

    create_response = api_client.post(
        "/api/v1/ml/petri-annotation-exports",
        json={
            "dataset_release_id": context["release_id"],
            "petri_segmentation_run_id": context["segmentation_run_id"],
            "config": {"export_format": "blueberry_manifest"},
        },
        headers={"X-Request-ID": "petri-annotation-export-request-1"},
    )

    assert create_response.status_code == 201
    assert create_response.headers["X-Request-ID"] == "petri-annotation-export-request-1"
    export_run = create_response.json()
    assert export_run["status"] == "completed"
    assert export_run["exported_annotation_count"] == 1
    assert export_run["output_manifest"]["category"]["name"] == "candidate_region"

    detail_response = api_client.get(f"/api/v1/ml/petri-annotation-exports/{export_run['id']}")
    assert detail_response.status_code == 200

    items_response = api_client.get(f"/api/v1/ml/petri-annotation-exports/{export_run['id']}/items")
    assert items_response.status_code == 200
    item = items_response.json()["items"][0]
    assert item["bbox_source"] == "corrected"
    assert item["export_label"] == "candidate_region"

    manifest_response = api_client.get(f"/api/v1/ml/petri-annotation-exports/{export_run['id']}/manifest")
    assert manifest_response.status_code == 200
    assert manifest_response.json()["annotations"][0]["bbox_source"] == "corrected"

    by_release = api_client.get(f"/api/v1/datasets/releases/{context['release_id']}/petri-annotation-exports")
    assert by_release.status_code == 200
    assert len(by_release.json()["exports"]) == 1

    by_segmentation = api_client.get(
        f"/api/v1/ml/petri-segmentations/{context['segmentation_run_id']}/annotation-exports"
    )
    assert by_segmentation.status_code == 200
    assert len(by_segmentation.json()["exports"]) == 1

    haystack = str(export_run).lower() + str(items_response.json()).lower()
    for word in _FORBIDDEN_TAXONOMY_WORDS:
        assert word not in haystack
    assert "pytorch" not in haystack
    assert "tensorflow" not in haystack


def test_creates_coco_and_yolo_annotation_exports(api_client):
    context = _create_segmentation_run_with_region(api_client, "PAE-COCO-YOLO")
    _create_valid_review(api_client, context)

    coco_response = api_client.post(
        "/api/v1/ml/petri-annotation-exports",
        json={
            "dataset_release_id": context["release_id"],
            "petri_segmentation_run_id": context["segmentation_run_id"],
            "config": {"export_format": "coco_json"},
        },
    )
    assert coco_response.status_code == 201
    assert coco_response.json()["output_manifest"]["categories"] == [{"id": 1, "name": "candidate_region"}]
    assert "segmentation" not in coco_response.json()["output_manifest"]["annotations"][0]

    yolo_response = api_client.post(
        "/api/v1/ml/petri-annotation-exports",
        json={
            "dataset_release_id": context["release_id"],
            "petri_segmentation_run_id": context["segmentation_run_id"],
            "config": {"export_format": "yolo_txt"},
        },
    )
    assert yolo_response.status_code == 201
    assert yolo_response.json()["output_manifest"]["format"] == "yolo_txt"
    assert yolo_response.json()["output_manifest"]["labels"][0]["lines"][0].startswith("0 ")


def test_annotation_export_rejects_segmentation_from_other_release(api_client):
    context_a = _create_segmentation_run_with_region(api_client, "PAE-ERR-A")
    context_b = _create_segmentation_run_with_region(api_client, "PAE-ERR-B")
    _create_valid_review(api_client, context_a)

    response = api_client.post(
        "/api/v1/ml/petri-annotation-exports",
        json={
            "dataset_release_id": context_b["release_id"],
            "petri_segmentation_run_id": context_a["segmentation_run_id"],
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "petri_annotation_export_not_allowed"


def test_annotation_export_rejects_invalid_format(api_client):
    context = _create_segmentation_run_with_region(api_client, "PAE-BAD-FORMAT")

    response = api_client.post(
        "/api/v1/ml/petri-annotation-exports",
        json={
            "dataset_release_id": context["release_id"],
            "petri_segmentation_run_id": context["segmentation_run_id"],
            "config": {"export_format": "not_real"},
        },
    )

    assert response.status_code == 422
