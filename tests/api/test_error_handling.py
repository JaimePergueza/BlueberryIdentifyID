from blueberry_microid.interfaces.api.v1.dependencies import get_get_sample_by_id_use_case
from tests.api.image_helpers import make_valid_jpeg_bytes


def _create_sample(api_client, sample_code: str) -> str:
    return api_client.post("/api/v1/samples", json={"sample_code": sample_code}).json()["id"]


class _AlwaysFailingUseCase:
    def execute(self, *_args, **_kwargs):
        raise RuntimeError("db password=hunter2 at /var/secrets/db.conf")


def test_generic_500_does_not_leak_internal_details(api_client):
    api_client.app.dependency_overrides[get_get_sample_by_id_use_case] = lambda: _AlwaysFailingUseCase()
    try:
        response = api_client.get("/api/v1/samples/00000000-0000-0000-0000-000000000000")
    finally:
        api_client.app.dependency_overrides.pop(get_get_sample_by_id_use_case, None)

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    message = body["error"]["message"]
    assert "hunter2" not in message
    assert "/var/secrets" not in message
    assert "RuntimeError" not in message


def test_invalid_image_still_returns_400(api_client):
    sample_id = _create_sample(api_client, "S-ERR-1")

    response = api_client.post(
        f"/api/v1/samples/{sample_id}/petri-images",
        files={"file": ("colony.jpg", b"not-a-real-image", "image/jpeg")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_image"
