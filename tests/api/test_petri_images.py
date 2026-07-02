from tests.api.image_helpers import make_valid_jpeg_bytes


def _create_sample(api_client, sample_code: str) -> str:
    return api_client.post("/api/v1/samples", json={"sample_code": sample_code}).json()["id"]


def test_register_petri_image_with_valid_data(api_client):
    sample_id = _create_sample(api_client, "S-PETRI-1")
    content = make_valid_jpeg_bytes(width=64, height=48)

    response = api_client.post(
        f"/api/v1/samples/{sample_id}/petri-images",
        files={"file": ("colony.jpg", content, "image/jpeg")},
        data={"culture_medium": "PDA", "observed_colony_color": "white"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["sample_id"] == sample_id
    assert body["culture_medium"] == "PDA"
    assert body["width"] == 64
    assert body["height"] == 48
    # The API computed this from the actual bytes — the client never sent it.
    assert body["file_size_bytes"] == len(content)


def test_register_petri_image_does_not_require_file_size_bytes_field(api_client):
    """The multipart request below never includes a file_size_bytes field —
    only `file` and optional metadata — proving the API computes it itself.
    """
    sample_id = _create_sample(api_client, "S-PETRI-2")
    content = make_valid_jpeg_bytes()

    response = api_client.post(
        f"/api/v1/samples/{sample_id}/petri-images",
        files={"file": ("colony.jpg", content, "image/jpeg")},
    )

    assert response.status_code == 201
    assert response.json()["file_size_bytes"] == len(content)


def test_register_petri_image_rejects_corrupted_image(api_client):
    sample_id = _create_sample(api_client, "S-PETRI-3")

    response = api_client.post(
        f"/api/v1/samples/{sample_id}/petri-images",
        files={"file": ("colony.jpg", b"not-a-real-image", "image/jpeg")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_image"


def test_register_petri_image_rejects_missing_sample(api_client):
    content = make_valid_jpeg_bytes()

    response = api_client.post(
        "/api/v1/samples/00000000-0000-0000-0000-000000000000/petri-images",
        files={"file": ("colony.jpg", content, "image/jpeg")},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "sample_not_found"


def test_register_petri_image_rejects_disallowed_mime_type(api_client):
    sample_id = _create_sample(api_client, "S-PETRI-4")
    content = make_valid_jpeg_bytes()

    response = api_client.post(
        f"/api/v1/samples/{sample_id}/petri-images",
        files={"file": ("colony.jpg", content, "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_image"
