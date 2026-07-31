from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from blueberry_microid.domain.entities.user import User
from blueberry_microid.domain.enums.user_role import UserRole


@dataclass(frozen=True, slots=True)
class UserDTO:
    id: UUID
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, user: User) -> "UserDTO":
        return cls(
            id=user.id,
            username=user.username,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


@dataclass(frozen=True, slots=True)
class LoginResultDTO:
    access_token: str
    token_type: str
    expires_at: datetime
    user: UserDTO
