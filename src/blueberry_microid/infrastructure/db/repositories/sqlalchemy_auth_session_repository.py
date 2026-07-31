from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.auth_session_repository import AuthSessionRepositoryPort
from blueberry_microid.domain.entities.auth_session import AuthSession
from blueberry_microid.infrastructure.db.models.auth_session import AuthSessionModel


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _to_entity(model: AuthSessionModel) -> AuthSession:
    return AuthSession(
        id=model.id,
        user_id=model.user_id,
        token_hash=model.token_hash,
        created_at=_aware(model.created_at),
        expires_at=_aware(model.expires_at),
        revoked_at=_aware(model.revoked_at) if model.revoked_at is not None else None,
    )


class SqlAlchemyAuthSessionRepository(AuthSessionRepositoryPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, session: AuthSession) -> AuthSession:
        model = AuthSessionModel(
            id=session.id,
            user_id=session.user_id,
            token_hash=session.token_hash,
            created_at=session.created_at,
            expires_at=session.expires_at,
            revoked_at=session.revoked_at,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _to_entity(model)

    def update(self, session: AuthSession) -> AuthSession:
        model = self._session.get(AuthSessionModel, session.id)
        if model is None:
            return session
        model.revoked_at = session.revoked_at
        model.expires_at = session.expires_at
        self._session.commit()
        self._session.refresh(model)
        return _to_entity(model)

    def get_by_token_hash(self, token_hash: str) -> Optional[AuthSession]:
        statement = select(AuthSessionModel).where(AuthSessionModel.token_hash == token_hash)
        model = self._session.scalar(statement)
        return _to_entity(model) if model is not None else None

    def revoke_all_for_user(self, user_id: UUID) -> int:
        now = datetime.now(timezone.utc)
        statement = (
            update(AuthSessionModel)
            .where(
                AuthSessionModel.user_id == user_id,
                AuthSessionModel.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        result = self._session.execute(statement)
        self._session.commit()
        return int(result.rowcount or 0)
