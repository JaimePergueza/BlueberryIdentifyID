from blueberry_microid.application.auth_exceptions import AuthenticationRequiredError
from blueberry_microid.application.ports.auth_session_repository import AuthSessionRepositoryPort
from blueberry_microid.application.ports.session_token_service import SessionTokenServicePort
from blueberry_microid.application.ports.user_repository import UserRepositoryPort
from blueberry_microid.domain.entities.user import User


class AuthenticateSessionUseCase:
    def __init__(
        self,
        user_repository: UserRepositoryPort,
        session_repository: AuthSessionRepositoryPort,
        token_service: SessionTokenServicePort,
    ) -> None:
        self._users = user_repository
        self._sessions = session_repository
        self._tokens = token_service

    def execute(self, raw_token: str) -> User:
        try:
            token_hash = self._tokens.hash_token(raw_token)
        except ValueError as exc:
            raise AuthenticationRequiredError("A valid bearer session is required") from exc

        session = self._sessions.get_by_token_hash(token_hash)
        if session is None or not session.is_valid():
            raise AuthenticationRequiredError("A valid bearer session is required")

        user = self._users.get_by_id(session.user_id)
        if user is None or not user.is_active:
            raise AuthenticationRequiredError("A valid bearer session is required")
        return user
