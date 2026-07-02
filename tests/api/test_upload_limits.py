from tests.api.image_helpers import make_valid_jpeg_bytes


def _create_sample(api_client, sample_code: str) -> str:
    return api_client.post("/api/v1/samples", json={"sample_code": sample_code}).json()["id"]


def test_upload_within_limit_succeeds(api_client):
    sample_id = _create_sample(api_client, "S-LIMIT-1")
    content = make_valid_jpeg_bytes()  # a few hundred bytes, well under the 20 MB default

    response = api_client.post(
        f"/api/v1/samples/{sample_id}/petri-images",
        files={"file": ("colony.jpg", content, "image/jpeg")},
    )

    assert response.status_code == 201


def test_upload_over_limit_returns_413(api_client):
    sample_id = _create_sample(api_client, "S-LIMIT-2")
    content = make_valid_jpeg_bytes()

    # Shrink the configured limit below this test's file size, instead of
    # generating a real 20 MB file — proves the limit is read from Settings
    # (not hardcoded) without making the test suite slow.
    original_settings = api_client.app.state.settings
    api_client.app.state.settings = original_settings.model_copy(
        update={"max_upload_size_mb": (len(content) - 1) / (1024 * 1024)}
    )
    try:
        response = api_client.post(
            f"/api/v1/samples/{sample_id}/petri-images",
            files={"file": ("colony.jpg", content, "image/jpeg")},
        )
    finally:
        api_client.app.state.settings = original_settings

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "image_too_large"


def test_micro_image_upload_over_limit_returns_413(api_client):
    sample_id = _create_sample(api_client, "S-LIMIT-3")
    content = make_valid_jpeg_bytes()

    original_settings = api_client.app.state.settings
    api_client.app.state.settings = original_settings.model_copy(
        update={"max_upload_size_mb": (len(content) - 1) / (1024 * 1024)}
    )
    try:
        response = api_client.post(
            f"/api/v1/samples/{sample_id}/micro-images",
            files={"file": ("hyphae.jpg", content, "image/jpeg")},
        )
    finally:
        api_client.app.state.settings = original_settings

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "image_too_large"
