from tests.api.image_helpers import make_valid_jpeg_bytes, make_valid_png_bytes


def _create_sample(api_client, sample_code: str) -> str:
    return api_client.post("/api/v1/samples", json={"sample_code": sample_code}).json()["id"]


def _create_model_version(api_client, name: str) -> str:
    return api_client.post(
        "/api/v1/model-versions", json={"name": name, "version": "0.1.0", "model_type": "mock"}
    ).json()["id"]


def _create_petri_image(api_client, sample_id: str) -> str:
    content = make_valid_jpeg_bytes()
    return api_client.post(
        f"/api/v1/samples/{sample_id}/petri-images",
        files={"file": ("colony.jpg", content, "image/jpeg")},
    ).json()["id"]


def _create_micro_image(api_client, sample_id: str) -> str:
    content = make_valid_png_bytes()
    return api_client.post(
        f"/api/v1/samples/{sample_id}/micro-images",
        files={"file": ("hyphae.png", content, "image/png")},
    ).json()["id"]


def test_create_analysis_run_with_valid_references(api_client):
    sample_id = _create_sample(api_client, "S-RUN-1")
    petri_image_id = _create_petri_image(api_client, sample_id)
    micro_image_id = _create_micro_image(api_client, sample_id)
    model_version_id = _create_model_version(api_client, "engine-run-1")

    response = api_client.post(
        "/api/v1/analysis-runs",
        json={
            "sample_id": sample_id,
            "petri_image_id": petri_image_id,
            "micro_image_id": micro_image_id,
            "model_version_id": model_version_id,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["sample_id"] == sample_id
    assert body["petri_image_id"] == petri_image_id
    assert body["micro_image_id"] == micro_image_id


def test_get_analysis_run(api_client):
    sample_id = _create_sample(api_client, "S-RUN-2")
    petri_image_id = _create_petri_image(api_client, sample_id)
    micro_image_id = _create_micro_image(api_client, sample_id)
    model_version_id = _create_model_version(api_client, "engine-run-2")
    created = api_client.post(
        "/api/v1/analysis-runs",
        json={
            "sample_id": sample_id,
            "petri_image_id": petri_image_id,
            "micro_image_id": micro_image_id,
            "model_version_id": model_version_id,
        },
    ).json()

    response = api_client.get(f"/api/v1/analysis-runs/{created['id']}")

    assert response.status_code == 200
    assert response.json()["status"] == "pending"


def test_get_analysis_run_not_found(api_client):
    response = api_client.get("/api/v1/analysis-runs/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "analysis_run_not_found"


def test_create_analysis_run_rejects_petri_and_micro_from_different_samples(api_client):
    sample_a = _create_sample(api_client, "S-RUN-3A")
    sample_b = _create_sample(api_client, "S-RUN-3B")
    petri_image_id = _create_petri_image(api_client, sample_a)
    micro_image_id = _create_micro_image(api_client, sample_b)
    model_version_id = _create_model_version(api_client, "engine-run-3")

    response = api_client.post(
        "/api/v1/analysis-runs",
        json={
            "sample_id": sample_a,
            "petri_image_id": petri_image_id,
            "micro_image_id": micro_image_id,
            "model_version_id": model_version_id,
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "image_sample_mismatch"


def test_create_analysis_run_rejects_missing_sample(api_client):
    sample_id = _create_sample(api_client, "S-RUN-4")
    petri_image_id = _create_petri_image(api_client, sample_id)
    micro_image_id = _create_micro_image(api_client, sample_id)
    model_version_id = _create_model_version(api_client, "engine-run-4")

    response = api_client.post(
        "/api/v1/analysis-runs",
        json={
            "sample_id": "00000000-0000-0000-0000-000000000000",
            "petri_image_id": petri_image_id,
            "micro_image_id": micro_image_id,
            "model_version_id": model_version_id,
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "sample_not_found"


def test_create_analysis_run_rejects_invalid_body(api_client):
    response = api_client.post("/api/v1/analysis-runs", json={"sample_id": "not-a-uuid"})

    assert response.status_code == 422
