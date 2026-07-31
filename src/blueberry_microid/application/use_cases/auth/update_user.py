from typing import Optional
from uuid import UUID

from blueberry_microid.application.auth_exceptions import LastActiveAdminError, UserNotFoundError
from blueberry_microid.application.dto.auth_dto import UserDTO
from blueberry_microid.application.ports.auth_session_repository import AuthSessionRepositoryPort
from blueberry_microid.application.ports.password_hasher import PasswordHasherPort
from blueberry_microid.application.ports.user_repository import UserRepositoryPort
from blueberry_microid.domain.enums.user_role import UserRole


class UpdateUserUseCase:
    def __init__(
        self,
        user_repository: UserRepositoryPort,
        session_repository: AuthSessionRepositoryPort,
        password_hasher: PasswordHasherPort,
    ) -> None:
        self._users = user_repository
        self._sessions = session_repository
        self._password_hasher = password_hasher

    def execute(
        self,
        user_id: UUID,
        *,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
        password: Optional[str] = None,
    ) -> UserDTO:
        user = self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(f"user '{user_id}' does not exist")

        removes_active_admin = (
            user.role == UserRole.ADMIN
            and user.is_active
            and (
                (role is not None and role != UserRole.ADMIN)
                or is_active is False
            )
        )
        if removes_active_admin:
            active_admins = [
                candidate
                for candidate in self._users.list_all()
                if candidate.role == UserRole.ADMIN and candidate.is_active
            ]
            if len(active_admins) <= 1:
                raise LastActiveAdminError(
                    "the last active administrator cannot be removed or deactivated"
                )

        revoke_sessions = False
        if role is not None and role != user.role:
            user.change_role(role)
            revoke_sessions = True
        if is_active is not None and is_active != user.is_active:
            user.activate() if is_active else user.deactivate()
            revoke_sessions = True
        if password is not None:
            user.replace_password_hash(self._password_hasher.hash(password))
            revoke_sessions = True

        # Fail closed: revoke active sessions before persisting a sensitive
        # account change. If the subsequent user update fails, the account may
        # retain its previous data, but no previously issued token remains valid.
        if revoke_sessions:
            self._sessions.revoke_all_for_user(user.id)

        saved = self._users.update(user)
        return UserDTO.from_entity(saved)
