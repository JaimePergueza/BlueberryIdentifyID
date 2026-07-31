"""Create deterministic, non-sensitive demonstration data through the deployed API.

The script is idempotent by sample code. It bootstraps the configured admin and
specialist directly in PostgreSQL, then uses the public Nginx entrypoint to
exercise login, paired image upload, automatic analysis and human review.
"""

from __future__ import annotations

import io
import json
import os
import random
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageDraw

from blueberry_microid.application.use_cases.auth.create_user import CreateUserUseCase
from blueberry_microid.domain.enums.user_role import UserRole
from blueberry_microid.infrastructure.config.settings import Settings
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_auth_session_repository import (
    SqlAlchemyAuthSessionRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_user_repository import (
    SqlAlchemyUserRepository,
)
from blueberry_microid.infrastructure.db.session.engine import create_db_engine
from blueberry_microid.infrastructure.db.session.session_factory import create_session_factory
from blueberry_microid.infrastructure.security.pwdlib_password_hasher import PwdlibPasswordHasher


class DemoSeedError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DemoCase:
    sample_code: str
    seed: int
    review_decision: str | None
    corrected_label: str | None = None


DEMO_CASES = (
    DemoCase("DEMO-BB-001", 11, "confirmed"),
    DemoCase("DEMO-BB-002", 22, "corrected", "inconclusive"),
    DemoCase("DEMO-BB-003", 33, None),
)


def _secret(name: str) -> str:
    value = os.getenv(name, "")
    if len(value) < 12 or value.startswith("CHANGE_ME"):
        raise DemoSeedError(
            f"{name} must be set to a non-placeholder value with at least 12 characters"
        )
    return value


def _upsert_user(username: str, password: str, role: UserRole) -> None:
    settings = Settings()
    engine = create_db_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    hasher = PwdlibPasswordHasher()
    with session_factory() as session:
        users = SqlAlchemyUserRepository(session)
        sessions = SqlAlchemyAuthSessionRepository(session)
        existing = users.get_by_username(username)
        if existing is None:
            CreateUserUseCase(users, hasher).execute(username, password, role)
            return
        existing.change_role(role)
        existing.activate()
        existing.replace_password_hash(hasher.hash(password))
        sessions.revoke_all_for_user(existing.id)
        users.update(existing)


def _request_json(
    base_url: str,
    method: str,
    path: str,
    *,
    token: str | None = None,
    body: bytes | None = None,
    content_type: str | None = None,
) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
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
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        raise DemoSeedError(f"{method} {path} failed with HTTP {exc.code}: {message}") from exc
    except urllib.error.URLError as exc:
        raise DemoSeedError(f"Could not connect to {base_url}: {exc}") from exc


def _login(base_url: str, username: str, password: str) -> str:
    body = urllib.parse.urlencode({"username": username, "password": password}).encode()
    payload = _request_json(
        base_url,
        "POST",
        "/api/v1/auth/login",
        body=body,
        content_type="application/x-www-form-urlencoded",
    )
    return str(payload["access_token"])


def _multipart(
    fields: dict[str, str],
    files: dict[str, tuple[str, str, bytes]],
) -> tuple[bytes, str]:
    boundary = f"----BlueberryDemo{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )
    for name, (filename, mime_type, content) in files.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                (
                    f'Content-Disposition: form-data; name="{name}"; '
                    f'filename="{filename}"\r\n'
                ).encode(),
                f"Content-Type: {mime_type}\r\n\r\n".encode(),
                content,
                b"\r\n",
            ]
        )
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def _petri_image(seed: int) -> bytes:
    randomizer = random.Random(seed)
    image = Image.new("RGB", (720, 540), "#d8d2bd")
    draw = ImageDraw.Draw(image)
    draw.ellipse((100, 30, 620, 510), fill="#efe9d4", outline="#53606a", width=8)
    draw.ellipse((125, 55, 595, 485), outline="#a49b83", width=3)
    palette = ("#535c3c", "#726443", "#9c8b68", "#3f4a35")
    for _ in range(20 + seed % 11):
        x = randomizer.randint(165, 545)
        y = randomizer.randint(95, 445)
        radius = randomizer.randint(5, 22)
        color = randomizer.choice(palette)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
    draw.text((22, 510), f"Synthetic demo plate {seed}", fill="#31383e")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def _micro_image(seed: int) -> bytes:
    randomizer = random.Random(seed * 3)
    image = Image.new("RGB", (720, 540), "#e6e1c8")
    draw = ImageDraw.Draw(image)
    for _ in range(90 + seed % 23):
        x = randomizer.randint(20, 700)
        y = randomizer.randint(20, 520)
        radius = randomizer.randint(2, 8)
        color = randomizer.choice(("#4c315a", "#31506f", "#70405b", "#395d57"))
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
    for _ in range(14):
        points = [
            (randomizer.randint(0, 720), randomizer.randint(0, 540))
            for _ in range(4)
        ]
        draw.line(points, fill="#596270", width=randomizer.randint(1, 3), joint="curve")
    draw.text((22, 510), f"Synthetic demo microscopy {seed}", fill="#31383e")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _already_seeded(base_url: str, token: str, sample_code: str) -> bool:
    query = urllib.parse.urlencode({"sample_code": sample_code, "page_size": 1})
    payload = _request_json(
        base_url,
        "GET",
        f"/api/v1/analysis-runs?{query}",
        token=token,
    )
    return int(payload.get("total", 0)) > 0


def _seed_case(base_url: str, token: str, case: DemoCase) -> None:
    if _already_seeded(base_url, token, case.sample_code):
        print(f"Demo sample {case.sample_code} already exists; skipping.")
        return

    body, content_type = _multipart(
        {
            "sample_code": case.sample_code,
            "notes": "Synthetic demonstration data. Not a real microbiology sample.",
        },
        {
            "petri_image": (
                f"{case.sample_code.lower()}-petri.jpg",
                "image/jpeg",
                _petri_image(case.seed),
            ),
            "micro_image": (
                f"{case.sample_code.lower()}-micro.png",
                "image/png",
                _micro_image(case.seed),
            ),
        },
    )
    upload = _request_json(
        base_url,
        "POST",
        "/api/v1/analysis/two-image-upload",
        token=token,
        body=body,
        content_type=content_type,
    )
    run_id = str(upload["analysis_run_id"])

    if case.review_decision:
        review_payload: dict[str, Any] = {
            "reviewer_name": "Especialista Demo",
            "review_decision": case.review_decision,
            "comments": "Revisión sintética preparada para la demostración del sistema.",
            "is_final": True,
        }
        if case.corrected_label:
            review_payload["corrected_label"] = case.corrected_label
        _request_json(
            base_url,
            "POST",
            f"/api/v1/analysis-runs/{run_id}/reviews",
            token=token,
            body=json.dumps(review_payload).encode("utf-8"),
            content_type="application/json",
        )
    print(f"Created synthetic demo analysis {case.sample_code} ({run_id}).")


def main() -> int:
    try:
        base_url = os.getenv("DEMO_BASE_URL", "http://127.0.0.1:8080")
        admin_username = os.getenv("BLUEBERRY_ADMIN_USERNAME", "admin-demo").strip().lower()
        specialist_username = os.getenv(
            "BLUEBERRY_SPECIALIST_USERNAME", "especialista-demo"
        ).strip().lower()
        admin_password = _secret("BLUEBERRY_ADMIN_PASSWORD")
        specialist_password = _secret("BLUEBERRY_SPECIALIST_PASSWORD")

        _upsert_user(admin_username, admin_password, UserRole.ADMIN)
        _upsert_user(specialist_username, specialist_password, UserRole.SPECIALIST)
        token = _login(base_url, admin_username, admin_password)
        for case in DEMO_CASES:
            _seed_case(base_url, token, case)
        print("Demo data is ready. Credentials were not printed.")
        return 0
    except (DemoSeedError, ValueError, KeyError) as exc:
        print(f"Demo seed failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
