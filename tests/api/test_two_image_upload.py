"""API tests for Fase 40.1: persistent two-image upload analysis."""

from tests.api.image_helpers import make_valid_jpeg_bytes, make_valid_png_bytes


def _upload(api_client, petri=None, micro=None, extra_data=None):
    petri = petri or make_valid_jpeg_bytes()
    micro = micro or make_valid_jpeg_bytes(color="green")
    files = {
        "petri_image": ("petri.jpg", petri, "image/jpeg"),
        "micro_image": ("micro.jpg", micro, "image/jpeg"),
    }
    return api_client.post("/api/v1/analysis/two-image-upload", files=files, data=extra_data or {})


def test_two_image_upload_returns_201_with_valid_images(api_client):
    response = _upload(api_client)

    assert response.status_code == 201
    body = response.json()
    assert "analysis_run_id" in body
    assert "sample_id" in body
    assert "petri_image_id" in body
    assert "micro_image_id" in body
    assert body["predicted_label"] in (
        "no_evident_growth",
        "suspicious_growth",
        "probable_fungal_growth",
        "probable_bacterial_growth",
        "inconclusive",
    )
    assert 0.0 < body["confidence_score"] <= 1.0
    assert len(body["class_probabilities"]) == 5
    assert body["requires_human_review"] is True
    assert body["disclaimer"]


def test_two_image_upload_accepts_png(api_client):
    petri = make_valid_png_bytes()
    micro = make_valid_png_bytes(color="red")
    files = {
        "petri_image": ("petri.png", petri, "image/png"),
        "micro_image": ("micro.png", micro, "image/png"),
    }
    response = api_client.post("/api/v1/analysis/two-image-upload", files=files)

    assert response.status_code == 201
    assert response.json()["analysis_run_id"]


def test_two_image_upload_always_requires_human_review(api_client):
    response = _upload(api_client)
    assert response.json()["requires_human_review"] is True


def test_two_image_upload_response_has_prediction_id(api_client):
    body = _upload(api_client).json()
    assert "prediction_id" in body
    assert body["prediction_id"]


def test_two_image_upload_persists_sample(api_client):
    body = _upload(api_client).json()
    sample_id = body["sample_id"]
    sample_response = api_client.get(f"/api/v1/samples/{sample_id}")
    assert sample_response.status_code == 200
    assert sample_response.json()["id"] == sample_id


def test_two_image_upload_persists_petri_and_micro_images(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    run_response = api_client.get(f"/api/v1/analysis-runs/{run_id}")
    assert run_response.status_code == 200
    run = run_response.json()
    assert run["petri_image_id"] == body["petri_image_id"]
    assert run["micro_image_id"] == body["micro_image_id"]


def test_two_image_upload_no_automatic_human_review(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    hr_response = api_client.get(f"/api/v1/analysis-runs/{run_id}/reviews")
    assert hr_response.status_code == 200
    body = hr_response.json()
    reviews = body.get("reviews", body) if isinstance(body, dict) else body
    assert reviews == []


def test_two_image_upload_with_custom_sample_code(api_client):
    response = _upload(api_client, extra_data={"sample_code": "PETRI-TEST-001"})
    assert response.status_code == 201
    body = response.json()
    sample_response = api_client.get(f"/api/v1/samples/{body['sample_id']}")
    assert sample_response.json()["sample_code"] == "PETRI-TEST-001"


def test_two_image_upload_rejects_corrupted_petri(api_client):
    micro = make_valid_jpeg_bytes()
    response = api_client.post(
        "/api/v1/analysis/two-image-upload",
        files={
            "petri_image": ("petri.jpg", b"not-an-image", "image/jpeg"),
            "micro_image": ("micro.jpg", micro, "image/jpeg"),
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_image"


def test_two_image_upload_rejects_corrupted_micro(api_client):
    petri = make_valid_jpeg_bytes()
    response = api_client.post(
        "/api/v1/analysis/two-image-upload",
        files={
            "petri_image": ("petri.jpg", petri, "image/jpeg"),
            "micro_image": ("micro.jpg", b"not-an-image", "image/jpeg"),
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_image"


def test_two_image_upload_response_contains_no_internal_path(api_client):
    body = _upload(api_client).json()
    body_str = str(body)
    for key in body:
        if isinstance(body[key], str):
            assert "\\" not in body[key] and ("/" not in body[key] or key == "disclaimer")


def test_two_image_upload_produces_unique_run_ids(api_client):
    r1 = _upload(api_client).json()
    r2 = _upload(api_client).json()
    assert r1["analysis_run_id"] != r2["analysis_run_id"]


def _setup_completed_analysis_run(api_client) -> str:
    """Create sample, register images, create AnalysisRun, and process it.
    Returns the analysis_run_id."""
    sample_id = api_client.post("/api/v1/samples", json={"sample_code": "S-PR-1"}).json()["id"]

    petri_content = make_valid_jpeg_bytes()
    micro_content = make_valid_jpeg_bytes(color="green")

    petri_id = api_client.post(
        f"/api/v1/samples/{sample_id}/petri-images",
        files={"file": ("colony.jpg", petri_content, "image/jpeg")},
    ).json()["id"]

    micro_id = api_client.post(
        f"/api/v1/samples/{sample_id}/micro-images",
        files={"file": ("micro.jpg", micro_content, "image/jpeg")},
    ).json()["id"]

    mv_id = api_client.post(
        "/api/v1/model-versions",
        json={"name": "MockV1", "version": "0.0.1", "model_type": "mock"},
    ).json()["id"]

    run_id = api_client.post(
        "/api/v1/analysis-runs",
        json={
            "sample_id": sample_id,
            "petri_image_id": petri_id,
            "micro_image_id": micro_id,
            "model_version_id": mv_id,
        },
    ).json()["id"]

    api_client.post(f"/api/v1/analysis-runs/{run_id}/process")
    return run_id


def test_get_preliminary_result_returns_200_for_completed_run(api_client):
    run_id = _setup_completed_analysis_run(api_client)

    response = api_client.get(f"/api/v1/analysis-runs/{run_id}/preliminary-result")

    assert response.status_code == 200
    body = response.json()
    assert body["analysis_run_id"] == run_id
    assert "predicted_label" in body
    assert body["disclaimer"]


def test_get_preliminary_result_404_for_pending_run(api_client):
    sample_id = api_client.post("/api/v1/samples", json={"sample_code": "S-PR-2"}).json()["id"]
    petri_content = make_valid_jpeg_bytes()
    micro_content = make_valid_jpeg_bytes(color="blue")
    petri_id = api_client.post(
        f"/api/v1/samples/{sample_id}/petri-images",
        files={"file": ("colony.jpg", petri_content, "image/jpeg")},
    ).json()["id"]
    micro_id = api_client.post(
        f"/api/v1/samples/{sample_id}/micro-images",
        files={"file": ("micro.jpg", micro_content, "image/jpeg")},
    ).json()["id"]
    mv_id = api_client.post(
        "/api/v1/model-versions",
        json={"name": "MockV1", "version": "0.0.2", "model_type": "mock"},
    ).json()["id"]
    run_id = api_client.post(
        "/api/v1/analysis-runs",
        json={
            "sample_id": sample_id,
            "petri_image_id": petri_id,
            "micro_image_id": micro_id,
            "model_version_id": mv_id,
        },
    ).json()["id"]

    response = api_client.get(f"/api/v1/analysis-runs/{run_id}/preliminary-result")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "prediction_not_found"


def test_get_preliminary_result_404_for_unknown_run(api_client):
    response = api_client.get(
        "/api/v1/analysis-runs/00000000-0000-0000-0000-000000000000/preliminary-result"
    )
    assert response.status_code == 404


def test_two_image_upload_analysis_run_is_retrievable(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    run_response = api_client.get(f"/api/v1/analysis-runs/{run_id}")
    assert run_response.status_code == 200
    assert run_response.json()["id"] == run_id
    assert run_response.json()["status"] in ("completed", "needs_review")


def test_two_image_upload_preliminary_result_retrievable(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    result_response = api_client.get(f"/api/v1/analysis-runs/{run_id}/preliminary-result")
    assert result_response.status_code == 200
    assert result_response.json()["requires_human_review"] is True
