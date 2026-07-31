from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from blueberry_microid.application.auth_exceptions import DuplicateUsernameError, UserNotFoundError
from blueberry_microid.application.ports.user_repository import UserRepositoryPort
from blueberry_microid.domain.entities.user import User
from blueberry_microid.infrastructure.db.models.user import UserModel


def _to_entity(model: UserModel) -> User:
    return User(
        id=model.id,
        username=model.username,
        password_hash=model.password_hash,
        role=model.role,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyUserRepository(UserRepositoryPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, user: User) -> User:
        model = UserModel(
            id=user.id,
            username=user.username,
            password_hash=user.password_hash,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        self._session.add(model)
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise DuplicateUsernameError(f"username '{user.username}' is already registered") from exc
        self._session.refresh(model)
        return _to_entity(model)

    def update(self, user: User) -> User:
        model = self._session.get(UserModel, user.id)
        if model is None:
            raise UserNotFoundError(f"user '{user.id}' does not exist")
        model.username = user.username
        model.password_hash = user.password_hash
        model.role = user.role
        model.is_active = user.is_active
        model.updated_at = user.updated_at
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise DuplicateUsernameError(f"username '{user.username}' is already registered") from exc
        self._session.refresh(model)
        return _to_entity(model)

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        model = self._session.get(UserModel, user_id)
        return _to_entity(model) if model is not None else None

    def get_by_username(self, username: str) -> Optional[User]:
        normalized = username.strip().lower()
        statement = select(UserModel).where(UserModel.username == normalized)
        model = self._session.scalar(statement)
        return _to_entity(model) if model is not None else None

    def list_all(self) -> list[User]:
        statement = select(UserModel).order_by(UserModel.username.asc(), UserModel.id.asc())
        return [_to_entity(model) for model in self._session.scalars(statement).all()]
