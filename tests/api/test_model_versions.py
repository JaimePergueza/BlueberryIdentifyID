def test_create_model_version_of_type_mock(api_client):
    response = api_client.post(
        "/api/v1/model-versions",
        json={"name": "stub-engine", "version": "0.1.0", "model_type": "mock"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["model_type"] == "mock"
    assert body["is_active"] is True


def test_create_model_version_rejects_invalid_model_type(api_client):
    response = api_client.post(
        "/api/v1/model-versions",
        json={"name": "bad-engine", "version": "0.1.0", "model_type": "tensorflow"},
    )

    # Rejected by schema-level enum validation before reaching the use
    # case, so this uses FastAPI's default validation error shape rather
    # than the {"error": {...}} shape used for domain/application errors.
    assert response.status_code == 422


def test_create_model_version_rejects_duplicate_name_and_version(api_client):
    payload = {"name": "stub-engine", "version": "0.2.0", "model_type": "mock"}
    api_client.post("/api/v1/model-versions", json=payload)

    response = api_client.post("/api/v1/model-versions", json=payload)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "duplicate_model_version"


def test_list_model_versions(api_client):
    api_client.post("/api/v1/model-versions", json={"name": "engine-a", "version": "1.0.0", "model_type": "mock"})
    api_client.post("/api/v1/model-versions", json={"name": "engine-b", "version": "1.0.0", "model_type": "external"})

    response = api_client.get("/api/v1/model-versions")

    assert response.status_code == 200
    names = {item["name"] for item in response.json()}
    assert {"engine-a", "engine-b"}.issubset(names)
