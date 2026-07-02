def test_create_sample_with_valid_data(api_client):
    response = api_client.post("/api/v1/samples", json={"sample_code": "S-API-100", "origin": "Field A"})

    assert response.status_code == 201
    body = response.json()
    assert body["sample_code"] == "S-API-100"
    assert body["product"] == "blueberry"
    assert body["origin"] == "Field A"
    assert "id" in body


def test_create_sample_rejects_duplicate_sample_code(api_client):
    api_client.post("/api/v1/samples", json={"sample_code": "S-API-101"})

    response = api_client.post("/api/v1/samples", json={"sample_code": "S-API-101"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "duplicate_sample_code"


def test_create_sample_rejects_empty_sample_code(api_client):
    response = api_client.post("/api/v1/samples", json={"sample_code": "   "})

    assert response.status_code == 422


def test_get_sample_by_id(api_client):
    created = api_client.post("/api/v1/samples", json={"sample_code": "S-API-102"}).json()

    response = api_client.get(f"/api/v1/samples/{created['id']}")

    assert response.status_code == 200
    assert response.json()["sample_code"] == "S-API-102"


def test_get_sample_by_id_not_found(api_client):
    response = api_client.get("/api/v1/samples/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "sample_not_found"


def test_get_sample_by_code(api_client):
    api_client.post("/api/v1/samples", json={"sample_code": "S-API-103"})

    response = api_client.get("/api/v1/samples/by-code/S-API-103")

    assert response.status_code == 200
    assert response.json()["sample_code"] == "S-API-103"


def test_get_sample_by_code_not_found(api_client):
    response = api_client.get("/api/v1/samples/by-code/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "sample_not_found"
