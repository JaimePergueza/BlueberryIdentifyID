import json
from uuid import UUID

from blueberry_microid.infrastructure.db.models.petri_image import PetriImageModel
from tests.api.image_helpers import make_valid_jpeg_bytes, make_valid_png_bytes


def _upload(api_client):
    petri = make_valid_jpeg_bytes(color="white")
    micro = make_valid_png_bytes(color="green")
    response = api_client.post(
        "/api/v1/analysis/two-image-upload",
        data={"sample_code": "CONTENT-TEST"},
        files={
            "petri_image": ("petri-original.jpg", petri, "image/jpeg"),
            "micro_image": ("micro-original.png", micro, "image/png"),
        },
    )
    assert response.status_code == 201, response.text
    return response.json(), petri, micro


def test_authenticated_user_can_read_both_stored_images(api_client):
    upload, petri, micro = _upload(api_client)

    petri_response = api_client.get(
        f"/api/v1/petri-images/{upload['petri_image_id']}/content"
    )
    micro_response = api_client.get(
        f"/api/v1/micro-images/{upload['micro_image_id']}/content"
    )

    assert petri_response.status_code == 200
    assert petri_response.content == petri
    assert petri_response.headers["content-type"] == "image/jpeg"
    assert petri_response.headers["content-disposition"] == 'inline; filename="petri-original.jpg"'
    assert micro_response.status_code == 200
    assert micro_response.content == micro
    assert micro_response.headers["content-type"] == "image/png"
    assert micro_response.headers["content-disposition"] == 'inline; filename="micro-original.png"'

    serialized_headers = json.dumps(dict(petri_response.headers)).lower()
    assert "storage" not in serialized_headers
    assert "file_path" not in serialized_headers


def test_anonymous_user_cannot_read_stored_image(api_client, anonymous_api_client):
    upload, _, _ = _upload(api_client)

    response = anonymous_api_client.get(
        f"/api/v1/petri-images/{upload['petri_image_id']}/content"
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


def test_unknown_image_returns_existing_controlled_not_found(api_client):
    response = api_client.get(
        "/api/v1/micro-images/00000000-0000-0000-0000-000000000000/content"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "micro_image_not_found"


def test_persisted_path_outside_allowed_storage_is_rejected(api_client, tmp_path):
    upload, _, _ = _upload(api_client)
    outside_file = tmp_path.parent / "outside-storage.jpg"
    outside_file.write_bytes(b"outside")

    with api_client.app.state.session_factory() as session:
        model = session.get(PetriImageModel, UUID(upload["petri_image_id"]))
        assert model is not None
        model.file_path = str(outside_file)
        session.commit()

    response = api_client.get(
        f"/api/v1/petri-images/{upload['petri_image_id']}/content"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "stored_image_unavailable"
    assert str(outside_file) not in response.text


def test_missing_stored_file_returns_controlled_error(api_client):
    upload, _, _ = _upload(api_client)

    with api_client.app.state.session_factory() as session:
        model = session.get(PetriImageModel, UUID(upload["petri_image_id"]))
        assert model is not None
        stored_path = model.file_path

    from pathlib import Path

    Path(stored_path).unlink()
    response = api_client.get(
        f"/api/v1/petri-images/{upload['petri_image_id']}/content"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "stored_image_unavailable"
