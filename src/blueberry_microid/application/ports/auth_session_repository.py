from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from blueberry_microid.domain.entities.auth_session import AuthSession


class AuthSessionRepositoryPort(ABC):
    """Persistence contract for revocable bearer sessions."""

    @abstractmethod
    def add(self, session: AuthSession) -> AuthSession:
        raise NotImplementedError

    @abstractmethod
    def update(self, session: AuthSession) -> AuthSession:
        raise NotImplementedError

    @abstractmethod
    def get_by_token_hash(self, token_hash: str) -> Optional[AuthSession]:
        raise NotImplementedError

    @abstractmethod
    def revoke_all_for_user(self, user_id: UUID) -> int:
        """Revoke every currently active session for a user and return the count."""
        raise NotImplementedError
