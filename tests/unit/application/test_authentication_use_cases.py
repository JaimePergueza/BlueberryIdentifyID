from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import pytest

from blueberry_microid.application.auth_exceptions import (
    AuthenticationRequiredError,
    InvalidCredentialsError,
    LastActiveAdminError,
)
from blueberry_microid.application.ports.auth_session_repository import AuthSessionRepositoryPort
from blueberry_microid.application.ports.user_repository import UserRepositoryPort
from blueberry_microid.application.use_cases.auth.authenticate_session import AuthenticateSessionUseCase
from blueberry_microid.application.use_cases.auth.create_user import CreateUserUseCase
from blueberry_microid.application.use_cases.auth.login import LoginUseCase
from blueberry_microid.application.use_cases.auth.update_user import UpdateUserUseCase
from blueberry_microid.domain.entities.auth_session import AuthSession
from blueberry_microid.domain.entities.user import User
from blueberry_microid.domain.enums.user_role import UserRole
from blueberry_microid.infrastructure.security.pwdlib_password_hasher import PwdlibPasswordHasher
from blueberry_microid.infrastructure.security.secure_session_token_service import SecureSessionTokenService


class _Users(UserRepositoryPort):
    def __init__(self) -> None:
        self.items: dict[UUID, User] = {}

    def add(self, user: User) -> User:
        self.items[user.id] = user
        return user

    def update(self, user: User) -> User:
        self.items[user.id] = user
        return user

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        return self.items.get(user_id)

    def get_by_username(self, username: str) -> Optional[User]:
        normalized = username.strip().lower()
        return next((user for user in self.items.values() if user.username == normalized), None)

    def list_all(self) -> list[User]:
        return list(self.items.values())


class _Sessions(AuthSessionRepositoryPort):
    def __init__(self) -> None:
        self.items: dict[str, AuthSession] = {}

    def add(self, session: AuthSession) -> AuthSession:
        self.items[session.token_hash] = session
        return session

    def update(self, session: AuthSession) -> AuthSession:
        self.items[session.token_hash] = session
        return session

    def get_by_token_hash(self, token_hash: str) -> Optional[AuthSession]:
        return self.items.get(token_hash)

    def revoke_all_for_user(self, user_id: UUID) -> int:
        count = 0
        for session in self.items.values():
            if session.user_id == user_id and session.revoked_at is None:
                session.revoke()
                count += 1
        return count


def test_login_issues_only_a_hash_to_persistence():
    users, sessions = _Users(), _Sessions()
    hasher = PwdlibPasswordHasher()
    user = CreateUserUseCase(users, hasher).execute(
        "operator",
        "Operator-Password-Example-42",
        UserRole.SPECIALIST,
    )
    token_service = SecureSessionTokenService()

    result = LoginUseCase(users, sessions, hasher, token_service, 12).execute(
        "OPERATOR",
        "Operator-Password-Example-42",
    )

    assert result.user.id == user.id
    assert result.access_token not in sessions.items
    assert token_service.hash_token(result.access_token) in sessions.items


def test_login_uses_same_generic_error_for_missing_inactive_and_wrong_password():
    users, sessions = _Users(), _Sessions()
    hasher = PwdlibPasswordHasher()
    token_service = SecureSessionTokenService()
    create = CreateUserUseCase(users, hasher)
    active = create.execute("active-user", "Active-Password-Example-42", UserRole.SPECIALIST)
    inactive_dto = create.execute("inactive-user", "Inactive-Password-Example-42", UserRole.SPECIALIST)
    inactive = users.get_by_id(inactive_dto.id)
    inactive.deactivate()
    users.update(inactive)
    login = LoginUseCase(users, sessions, hasher, token_service, 12)

    for username, password in [
        ("missing", "Any-Password-Example-42"),
        (active.username, "Wrong-Password-Example-42"),
        (inactive.username, "Inactive-Password-Example-42"),
    ]:
        with pytest.raises(InvalidCredentialsError, match="Invalid username or password"):
            login.execute(username, password)


def test_authentication_rejects_expired_revoked_and_inactive_sessions():
    users, sessions = _Users(), _Sessions()
    hasher = PwdlibPasswordHasher()
    token_service = SecureSessionTokenService()
    dto = CreateUserUseCase(users, hasher).execute(
        "auth-user",
        "Authentication-Password-42",
        UserRole.SPECIALIST,
    )
    authenticate = AuthenticateSessionUseCase(users, sessions, token_service)

    expired = token_service.issue()
    sessions.add(
        AuthSession(
            user_id=dto.id,
            token_hash=expired.token_hash,
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
    )
    with pytest.raises(AuthenticationRequiredError):
        authenticate.execute(expired.raw_token)

    revoked = token_service.issue()
    revoked_session = AuthSession(
        user_id=dto.id,
        token_hash=revoked.token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    revoked_session.revoke()
    sessions.add(revoked_session)
    with pytest.raises(AuthenticationRequiredError):
        authenticate.execute(revoked.raw_token)

    active_token = token_service.issue()
    sessions.add(
        AuthSession(
            user_id=dto.id,
            token_hash=active_token.token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
    )
    user = users.get_by_id(dto.id)
    user.deactivate()
    users.update(user)
    with pytest.raises(AuthenticationRequiredError):
        authenticate.execute(active_token.raw_token)


def test_last_active_admin_cannot_be_deactivated_or_demoted():
    users, sessions = _Users(), _Sessions()
    hasher = PwdlibPasswordHasher()
    admin = CreateUserUseCase(users, hasher).execute(
        "only-admin",
        "Administrator-Password-42",
        UserRole.ADMIN,
    )
    update = UpdateUserUseCase(users, sessions, hasher)

    with pytest.raises(LastActiveAdminError):
        update.execute(admin.id, is_active=False)
    with pytest.raises(LastActiveAdminError):
        update.execute(admin.id, role=UserRole.SPECIALIST)


def test_password_change_revokes_existing_sessions():
    users, sessions = _Users(), _Sessions()
    hasher = PwdlibPasswordHasher()
    token_service = SecureSessionTokenService()
    first_admin = CreateUserUseCase(users, hasher).execute(
        "first-admin", "First-Administrator-Password-42", UserRole.ADMIN
    )
    CreateUserUseCase(users, hasher).execute(
        "second-admin", "Second-Administrator-Password-42", UserRole.ADMIN
    )
    issued = token_service.issue()
    sessions.add(
        AuthSession(
            user_id=first_admin.id,
            token_hash=issued.token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
    )

    UpdateUserUseCase(users, sessions, hasher).execute(
        first_admin.id,
        password="Replacement-Administrator-Password-42",
    )

    assert not sessions.get_by_token_hash(issued.token_hash).is_valid()
