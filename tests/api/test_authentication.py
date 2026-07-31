import json

from fastapi.testclient import TestClient

from blueberry_microid.infrastructure.config.settings import Settings
from blueberry_microid.interfaces.api import app as app_module


def test_health_and_login_are_public(anonymous_api_client):
    assert anonymous_api_client.get("/health").status_code == 200

    response = anonymous_api_client.post(
        "/api/v1/auth/login",
        data={"username": "missing-user", "password": "not-the-right-password"},
    )
    assert response.status_code == 401
    assert response.json()["error"] == {
        "code": "invalid_credentials",
        "message": "Invalid username or password",
        "request_id": response.json()["error"]["request_id"],
    }
    assert response.headers["www-authenticate"] == "Bearer"


def test_anonymous_operational_request_is_rejected(anonymous_api_client):
    response = anonymous_api_client.get("/api/v1/analysis-runs")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"
    assert response.headers["www-authenticate"] == "Bearer"


def test_login_me_and_logout_revoke_the_current_session(api_app):
    from tests.api.conftest import _TEST_PASSWORD, _create_user
    from blueberry_microid.domain.enums.user_role import UserRole

    _create_user(api_app, "session-user", UserRole.SPECIALIST)
    with TestClient(api_app, raise_server_exceptions=False) as client:
        login = client.post(
            "/api/v1/auth/login",
            data={"username": "SESSION-USER", "password": _TEST_PASSWORD},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        assert login.json()["token_type"] == "bearer"
        assert login.json()["user"]["username"] == "session-user"
        assert "password" not in json.dumps(login.json()).lower()

        headers = {"Authorization": f"Bearer {token}"}
        me = client.get("/api/v1/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["role"] == "specialist"

        logout = client.post("/api/v1/auth/logout", headers=headers)
        assert logout.status_code == 200
        assert logout.json() == {"message": "Session revoked"}

        after_logout = client.get("/api/v1/auth/me", headers=headers)
        assert after_logout.status_code == 401
        assert after_logout.json()["error"]["code"] == "authentication_required"


def test_specialist_can_use_core_flow_but_not_admin_routes(specialist_api_client):
    history = specialist_api_client.get("/api/v1/analysis-runs")
    admin_users = specialist_api_client.get("/api/v1/admin/users")
    model_versions = specialist_api_client.get("/api/v1/model-versions")

    assert history.status_code == 200
    assert admin_users.status_code == 403
    assert model_versions.status_code == 403
    assert admin_users.json()["error"]["code"] == "permission_denied"


def test_admin_can_create_list_and_deactivate_user(api_client, anonymous_api_client):
    created = api_client.post(
        "/api/v1/admin/users",
        json={
            "username": "new-specialist",
            "password": "Long-Specialist-Password-42",
            "role": "specialist",
        },
    )
    assert created.status_code == 201
    user = created.json()
    assert user["username"] == "new-specialist"
    assert user["role"] == "specialist"
    assert "password" not in json.dumps(user).lower()

    listed = api_client.get("/api/v1/admin/users")
    assert listed.status_code == 200
    assert {item["username"] for item in listed.json()["users"]} == {
        "new-specialist",
        "test-admin",
    }

    login = anonymous_api_client.post(
        "/api/v1/auth/login",
        data={"username": "new-specialist", "password": "Long-Specialist-Password-42"},
    )
    assert login.status_code == 200
    specialist_token = login.json()["access_token"]

    deactivated = api_client.patch(
        f"/api/v1/admin/users/{user['id']}",
        json={"is_active": False},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    rejected_session = anonymous_api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {specialist_token}"},
    )
    assert rejected_session.status_code == 401

    rejected_login = anonymous_api_client.post(
        "/api/v1/auth/login",
        data={"username": "new-specialist", "password": "Long-Specialist-Password-42"},
    )
    assert rejected_login.status_code == 401


def test_duplicate_username_and_last_admin_are_controlled(api_client):
    duplicate = api_client.post(
        "/api/v1/admin/users",
        json={
            "username": "TEST-ADMIN",
            "password": "Another-Long-Password-42",
            "role": "specialist",
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "duplicate_username"

    current = api_client.get("/api/v1/auth/me").json()
    last_admin = api_client.patch(
        f"/api/v1/admin/users/{current['id']}",
        json={"is_active": False},
    )
    assert last_admin.status_code == 409
    assert last_admin.json()["error"]["code"] == "last_active_admin"


def test_production_disables_interactive_api_documentation(monkeypatch, tmp_path):
    settings = Settings(
        _env_file=None,
        environment="production",
        database_url="sqlite://",
        storage_root=tmp_path,
    )
    monkeypatch.setattr(app_module, "get_settings", lambda: settings)

    app = app_module.create_app()

    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.openapi_url is None
