def test_response_includes_x_request_id_header(api_client):
    response = api_client.get("/health")

    assert "x-request-id" in response.headers
    assert len(response.headers["x-request-id"]) > 0


def test_client_supplied_request_id_is_preserved(api_client):
    response = api_client.get("/health", headers={"X-Request-ID": "client-supplied-id-123"})

    assert response.headers["x-request-id"] == "client-supplied-id-123"


def test_different_requests_get_different_request_ids(api_client):
    first = api_client.get("/health")
    second = api_client.get("/health")

    assert first.headers["x-request-id"] != second.headers["x-request-id"]


def test_error_responses_also_include_x_request_id(api_client):
    response = api_client.get("/api/v1/samples/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert "x-request-id" in response.headers
