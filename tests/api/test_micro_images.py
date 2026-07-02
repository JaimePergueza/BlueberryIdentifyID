from tests.api.image_helpers import make_valid_png_bytes


def _create_sample(api_client, sample_code: str) -> str:
    return api_client.post("/api/v1/samples", json={"sample_code": sample_code}).json()["id"]


def test_register_micro_image_with_valid_data(api_client):
    sample_id = _create_sample(api_client, "S-MICRO-1")
    content = make_valid_png_bytes(width=80, height=60)

    response = api_client.post(
        f"/api/v1/samples/{sample_id}/micro-images",
        files={"file": ("hyphae.png", content, "image/png")},
        data={"magnification": "400x", "observed_structures": "filamentous structures, unstained"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["sample_id"] == sample_id
    assert body["magnification"] == "400x"
    assert body["width"] == 80
    assert body["height"] == 60
    # The API computed this from the actual bytes — the client never sent it.
    assert body["file_size_bytes"] == len(content)


def test_register_micro_image_does_not_require_file_size_bytes_field(api_client):
    sample_id = _create_sample(api_client, "S-MICRO-2")
    content = make_valid_png_bytes()

    response = api_client.post(
        f"/api/v1/samples/{sample_id}/micro-images",
        files={"file": ("hyphae.png", content, "image/png")},
    )

    assert response.status_code == 201
    assert response.json()["file_size_bytes"] == len(content)


def test_register_micro_image_rejects_missing_sample(api_client):
    content = make_valid_png_bytes()

    response = api_client.post(
        "/api/v1/samples/00000000-0000-0000-0000-000000000000/micro-images",
        files={"file": ("hyphae.png", content, "image/png")},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "sample_not_found"


def test_register_micro_image_rejects_corrupted_image(api_client):
    sample_id = _create_sample(api_client, "S-MICRO-3")

    response = api_client.post(
        f"/api/v1/samples/{sample_id}/micro-images",
        files={"file": ("hyphae.png", b"definitely-not-a-png", "image/png")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_image"
