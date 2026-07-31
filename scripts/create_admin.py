"""Create the first BlueberryMicroID administrator without default credentials.

Run after `alembic upgrade head`. Credentials can be supplied through
BLUEBERRY_ADMIN_USERNAME and BLUEBERRY_ADMIN_PASSWORD. When omitted, the
script prompts interactively and hides the password input.
"""

from __future__ import annotations

import getpass
import os
import sys

from blueberry_microid.application.auth_exceptions import DuplicateUsernameError
from blueberry_microid.application.use_cases.auth.create_user import CreateUserUseCase
from blueberry_microid.domain.enums.user_role import UserRole
from blueberry_microid.infrastructure.config.settings import get_settings
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_user_repository import (
    SqlAlchemyUserRepository,
)
from blueberry_microid.infrastructure.db.session.engine import create_db_engine
from blueberry_microid.infrastructure.db.session.session_factory import create_session_factory
from blueberry_microid.infrastructure.security.pwdlib_password_hasher import PwdlibPasswordHasher


def _credentials() -> tuple[str, str]:
    username = os.getenv("BLUEBERRY_ADMIN_USERNAME") or input("Administrator username: ").strip()
    password = os.getenv("BLUEBERRY_ADMIN_PASSWORD")
    if password is None:
        password = getpass.getpass("Administrator password (minimum 12 characters): ")
        confirmation = getpass.getpass("Confirm password: ")
        if password != confirmation:
            raise ValueError("password confirmation does not match")
    return username, password


def main() -> int:
    try:
        username, password = _credentials()
        settings = get_settings()
        engine = create_db_engine(settings.database_url)
        session_factory = create_session_factory(engine)
        with session_factory() as session:
            use_case = CreateUserUseCase(
                SqlAlchemyUserRepository(session),
                PwdlibPasswordHasher(),
            )
            user = use_case.execute(username, password, UserRole.ADMIN)
        print(f"Created administrator '{user.username}' ({user.id}).")
        return 0
    except (ValueError, DuplicateUsernameError) as exc:
        print(f"Administrator was not created: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
