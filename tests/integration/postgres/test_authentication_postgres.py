from datetime import datetime, timedelta, timezone

import pytest

from blueberry_microid.application.auth_exceptions import DuplicateUsernameError
from blueberry_microid.domain.entities.auth_session import AuthSession
from blueberry_microid.domain.entities.user import User
from blueberry_microid.domain.enums.user_role import UserRole
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_auth_session_repository import (
    SqlAlchemyAuthSessionRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_user_repository import (
    SqlAlchemyUserRepository,
)
from blueberry_microid.infrastructure.security.pwdlib_password_hasher import PwdlibPasswordHasher
from blueberry_microid.infrastructure.security.secure_session_token_service import SecureSessionTokenService

pytestmark = pytest.mark.postgres


def test_user_role_password_hash_and_session_round_trip(pg_session):
    hasher = PwdlibPasswordHasher()
    users = SqlAlchemyUserRepository(pg_session)
    sessions = SqlAlchemyAuthSessionRepository(pg_session)
    tokens = SecureSessionTokenService()

    user = users.add(
        User(
            username="PG-Specialist",
            password_hash=hasher.hash("Postgres-Password-Example-42"),
            role=UserRole.SPECIALIST,
        )
    )
    issued = tokens.issue()
    auth_session = sessions.add(
        AuthSession(
            user_id=user.id,
            token_hash=issued.token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
    )

    loaded_user = users.get_by_username("pg-specialist")
    loaded_session = sessions.get_by_token_hash(tokens.hash_token(issued.raw_token))

    assert loaded_user is not None
    assert loaded_user.role == UserRole.SPECIALIST
    assert loaded_user.password_hash != "Postgres-Password-Example-42"
    assert hasher.verify("Postgres-Password-Example-42", loaded_user.password_hash)
    assert loaded_session is not None
    assert loaded_session.id == auth_session.id
    assert loaded_session.is_valid()


def test_postgres_enforces_normalized_username_uniqueness(pg_session):
    users = SqlAlchemyUserRepository(pg_session)
    hasher = PwdlibPasswordHasher()
    users.add(
        User(
            username="unique-admin",
            password_hash=hasher.hash("Unique-Administrator-Password-42"),
            role=UserRole.ADMIN,
        )
    )

    with pytest.raises(DuplicateUsernameError):
        users.add(
            User(
                username=" UNIQUE-ADMIN ",
                password_hash=hasher.hash("Different-Administrator-Pass-42"),
                role=UserRole.ADMIN,
            )
        )


def test_revoke_all_sessions_is_persisted(pg_session):
    users = SqlAlchemyUserRepository(pg_session)
    sessions = SqlAlchemyAuthSessionRepository(pg_session)
    hasher = PwdlibPasswordHasher()
    tokens = SecureSessionTokenService()
    user = users.add(
        User(
            username="revocation-user",
            password_hash=hasher.hash("Revocation-Password-Example-42"),
            role=UserRole.SPECIALIST,
        )
    )

    issued_tokens = [tokens.issue(), tokens.issue()]
    for issued in issued_tokens:
        sessions.add(
            AuthSession(
                user_id=user.id,
                token_hash=issued.token_hash,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
        )

    assert sessions.revoke_all_for_user(user.id) == 2
    assert all(
        not sessions.get_by_token_hash(issued.token_hash).is_valid()
        for issued in issued_tokens
    )
