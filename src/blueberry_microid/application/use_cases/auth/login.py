from datetime import datetime, timedelta, timezone

from blueberry_microid.application.auth_exceptions import InvalidCredentialsError
from blueberry_microid.application.dto.auth_dto import LoginResultDTO, UserDTO
from blueberry_microid.application.ports.auth_session_repository import AuthSessionRepositoryPort
from blueberry_microid.application.ports.password_hasher import PasswordHasherPort
from blueberry_microid.application.ports.session_token_service import SessionTokenServicePort
from blueberry_microid.application.ports.user_repository import UserRepositoryPort
from blueberry_microid.domain.entities.auth_session import AuthSession


class LoginUseCase:
    def __init__(
        self,
        user_repository: UserRepositoryPort,
        session_repository: AuthSessionRepositoryPort,
        password_hasher: PasswordHasherPort,
        token_service: SessionTokenServicePort,
        session_ttl_hours: int,
    ) -> None:
        self._users = user_repository
        self._sessions = session_repository
        self._password_hasher = password_hasher
        self._tokens = token_service
        self._session_ttl_hours = session_ttl_hours

    def execute(self, username: str, password: str) -> LoginResultDTO:
        user = self._users.get_by_username(username)
        if user is None or not user.is_active:
            raise InvalidCredentialsError("Invalid username or password")
        if not self._password_hasher.verify(password, user.password_hash):
            raise InvalidCredentialsError("Invalid username or password")

        issued = self._tokens.issue()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=self._session_ttl_hours)
        self._sessions.add(
            AuthSession(
                user_id=user.id,
                token_hash=issued.token_hash,
                expires_at=expires_at,
            )
        )
        return LoginResultDTO(
            access_token=issued.raw_token,
            token_type="bearer",
            expires_at=expires_at,
            user=UserDTO.from_entity(user),
        )
