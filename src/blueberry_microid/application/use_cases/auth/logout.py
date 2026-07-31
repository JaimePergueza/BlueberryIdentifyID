from blueberry_microid.application.ports.auth_session_repository import AuthSessionRepositoryPort
from blueberry_microid.application.ports.session_token_service import SessionTokenServicePort


class LogoutUseCase:
    def __init__(
        self,
        session_repository: AuthSessionRepositoryPort,
        token_service: SessionTokenServicePort,
    ) -> None:
        self._sessions = session_repository
        self._tokens = token_service

    def execute(self, raw_token: str) -> None:
        token_hash = self._tokens.hash_token(raw_token)
        session = self._sessions.get_by_token_hash(token_hash)
        if session is None:
            return
        if session.revoked_at is None:
            session.revoke()
            self._sessions.update(session)
