from functools import lru_cache
from typing import Optional

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from blueberry_microid.application.auth_exceptions import (
    AuthenticationRequiredError,
    PermissionDeniedError,
)
from blueberry_microid.application.ports.auth_session_repository import AuthSessionRepositoryPort
from blueberry_microid.application.ports.password_hasher import PasswordHasherPort
from blueberry_microid.application.ports.session_token_service import SessionTokenServicePort
from blueberry_microid.application.ports.user_repository import UserRepositoryPort
from blueberry_microid.application.use_cases.auth.authenticate_session import AuthenticateSessionUseCase
from blueberry_microid.application.use_cases.auth.create_user import CreateUserUseCase
from blueberry_microid.application.use_cases.auth.list_users import ListUsersUseCase
from blueberry_microid.application.use_cases.auth.login import LoginUseCase
from blueberry_microid.application.use_cases.auth.logout import LogoutUseCase
from blueberry_microid.application.use_cases.auth.update_user import UpdateUserUseCase
from blueberry_microid.domain.entities.user import User
from blueberry_microid.domain.enums.user_role import UserRole
from blueberry_microid.infrastructure.config.settings import Settings
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_auth_session_repository import (
    SqlAlchemyAuthSessionRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_user_repository import (
    SqlAlchemyUserRepository,
)
from blueberry_microid.infrastructure.security.pwdlib_password_hasher import PwdlibPasswordHasher
from blueberry_microid.infrastructure.security.secure_session_token_service import SecureSessionTokenService
from blueberry_microid.interfaces.api.v1.dependencies import get_db_session, get_settings_dependency


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


@lru_cache
def get_password_hasher() -> PasswordHasherPort:
    return PwdlibPasswordHasher()


@lru_cache
def get_session_token_service() -> SessionTokenServicePort:
    return SecureSessionTokenService()


def get_user_repository(session: Session = Depends(get_db_session)) -> UserRepositoryPort:
    return SqlAlchemyUserRepository(session)


def get_auth_session_repository(
    session: Session = Depends(get_db_session),
) -> AuthSessionRepositoryPort:
    return SqlAlchemyAuthSessionRepository(session)


def get_authenticate_session_use_case(
    users: UserRepositoryPort = Depends(get_user_repository),
    sessions: AuthSessionRepositoryPort = Depends(get_auth_session_repository),
    tokens: SessionTokenServicePort = Depends(get_session_token_service),
) -> AuthenticateSessionUseCase:
    return AuthenticateSessionUseCase(users, sessions, tokens)


def get_current_raw_token(token: Optional[str] = Depends(oauth2_scheme)) -> str:
    if token is None:
        raise AuthenticationRequiredError("A valid bearer session is required")
    return token


def get_current_user(
    raw_token: str = Depends(get_current_raw_token),
    use_case: AuthenticateSessionUseCase = Depends(get_authenticate_session_use_case),
) -> User:
    return use_case.execute(raw_token)


def require_specialist(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in {UserRole.SPECIALIST, UserRole.ADMIN}:
        raise PermissionDeniedError("This operation requires specialist access")
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise PermissionDeniedError("This operation requires administrator access")
    return current_user


def get_login_use_case(
    settings: Settings = Depends(get_settings_dependency),
    users: UserRepositoryPort = Depends(get_user_repository),
    sessions: AuthSessionRepositoryPort = Depends(get_auth_session_repository),
    password_hasher: PasswordHasherPort = Depends(get_password_hasher),
    tokens: SessionTokenServicePort = Depends(get_session_token_service),
) -> LoginUseCase:
    return LoginUseCase(
        users,
        sessions,
        password_hasher,
        tokens,
        settings.auth_session_ttl_hours,
    )


def get_logout_use_case(
    sessions: AuthSessionRepositoryPort = Depends(get_auth_session_repository),
    tokens: SessionTokenServicePort = Depends(get_session_token_service),
) -> LogoutUseCase:
    return LogoutUseCase(sessions, tokens)


def get_create_user_use_case(
    users: UserRepositoryPort = Depends(get_user_repository),
    password_hasher: PasswordHasherPort = Depends(get_password_hasher),
) -> CreateUserUseCase:
    return CreateUserUseCase(users, password_hasher)


def get_list_users_use_case(
    users: UserRepositoryPort = Depends(get_user_repository),
) -> ListUsersUseCase:
    return ListUsersUseCase(users)


def get_update_user_use_case(
    users: UserRepositoryPort = Depends(get_user_repository),
    sessions: AuthSessionRepositoryPort = Depends(get_auth_session_repository),
    password_hasher: PasswordHasherPort = Depends(get_password_hasher),
) -> UpdateUserUseCase:
    return UpdateUserUseCase(users, sessions, password_hasher)
