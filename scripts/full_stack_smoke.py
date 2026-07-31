"""Validate the deployed MVP through its single public frontend origin."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class FullStackSmokeError(RuntimeError):
    pass


def _secret(name: str) -> str:
    value = os.getenv(name, "")
    if len(value) < 12 or value.startswith("CHANGE_ME"):
        raise FullStackSmokeError(f"{name} must be a non-placeholder secret")
    return value


def _request(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    token: str | None = None,
    body: bytes | None = None,
    content_type: str | None = None,
) -> tuple[int, dict[str, str], bytes]:
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if content_type:
        headers["Content-Type"] = content_type
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, dict(response.headers.items()), response.read()
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        raise FullStackSmokeError(
            f"{method} {path} failed with HTTP {exc.code}: {payload}"
        ) from exc
    except urllib.error.URLError as exc:
        raise FullStackSmokeError(f"Could not connect to {base_url}: {exc}") from exc


def _json(*args, **kwargs) -> dict[str, Any]:
    status, _, body = _request(*args, **kwargs)
    if not 200 <= status < 300:
        raise FullStackSmokeError(f"Unexpected status {status}")
    return json.loads(body) if body else {}


def _login(base_url: str, username: str, password: str) -> str:
    payload = _json(
        base_url,
        "/api/v1/auth/login",
        method="POST",
        body=urllib.parse.urlencode({"username": username, "password": password}).encode(),
        content_type="application/x-www-form-urlencoded",
    )
    return str(payload["access_token"])


def _verify_image(
    base_url: str,
    token: str,
    path: str,
    expected_prefix: str,
) -> None:
    status, headers, content = _request(base_url, path, token=token)
    if status != 200:
        raise FullStackSmokeError(f"Image endpoint {path} returned {status}")
    content_type = headers.get("Content-Type", "")
    if not content_type.startswith(expected_prefix):
        raise FullStackSmokeError(
            f"Image endpoint {path} returned unexpected Content-Type {content_type!r}"
        )
    if len(content) < 500:
        raise FullStackSmokeError(f"Image endpoint {path} returned an unexpectedly small file")
    serialized_headers = json.dumps(headers).lower()
    if "file_path" in serialized_headers or "/app/storage" in serialized_headers:
        raise FullStackSmokeError("Image endpoint leaked an internal storage path")


def run() -> None:
    base_url = os.getenv("DEMO_BASE_URL", "http://127.0.0.1:8080")
    admin_username = os.getenv("BLUEBERRY_ADMIN_USERNAME", "admin-demo")
    admin_password = _secret("BLUEBERRY_ADMIN_PASSWORD")
    specialist_username = os.getenv("BLUEBERRY_SPECIALIST_USERNAME", "especialista-demo")
    specialist_password = _secret("BLUEBERRY_SPECIALIST_PASSWORD")

    status, _, html = _request(base_url, "/")
    if status != 200 or b"BlueberryMicroID" not in html:
        raise FullStackSmokeError("The frontend SPA is not available from the public origin")

    health = _json(base_url, "/health")
    if health.get("status") != "ok":
        raise FullStackSmokeError(f"Unexpected health response: {health!r}")

    admin_token = _login(base_url, admin_username, admin_password)
    specialist_token = _login(base_url, specialist_username, specialist_password)

    users = _json(base_url, "/api/v1/admin/users", token=admin_token)
    usernames = {item["username"] for item in users.get("users", [])}
    if {admin_username.lower(), specialist_username.lower()} - usernames:
        raise FullStackSmokeError("Demo users are missing from administrator user management")

    query = urllib.parse.urlencode({"sample_code": "DEMO-BB-001", "page_size": 10})
    history = _json(
        base_url,
        f"/api/v1/analysis-runs?{query}",
        token=specialist_token,
    )
    if history.get("total") != 1:
        raise FullStackSmokeError(f"Expected one DEMO-BB-001 analysis, got {history!r}")
    item = history["items"][0]
    if item.get("review_status") != "reviewed":
        raise FullStackSmokeError("DEMO-BB-001 should have a final human review")

    run_id = item["analysis_run_id"]
    detail = _json(
        base_url,
        f"/api/v1/analysis-runs/{run_id}/detail",
        token=specialist_token,
    )
    if detail["sample"]["sample_code"] != "DEMO-BB-001":
        raise FullStackSmokeError("Detail response belongs to the wrong sample")
    if detail.get("human_review") is None:
        raise FullStackSmokeError("Detail response did not include the final human review")

    _verify_image(
        base_url,
        specialist_token,
        f"/api/v1/petri-images/{detail['petri_image']['id']}/content",
        "image/jpeg",
    )
    _verify_image(
        base_url,
        specialist_token,
        f"/api/v1/micro-images/{detail['micro_image']['id']}/content",
        "image/png",
    )

    print("SUCCESS: full-stack MVP smoke passed through the public frontend origin.")
    print(f"Sample: {detail['sample']['sample_code']}")
    print(f"AnalysisRun: {run_id}")


def main() -> int:
    try:
        run()
        return 0
    except (FullStackSmokeError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"Full-stack smoke failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
