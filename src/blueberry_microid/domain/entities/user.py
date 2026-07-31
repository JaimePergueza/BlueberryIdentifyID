from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from blueberry_microid.domain.enums.user_role import UserRole


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class User:
    """Authenticated BlueberryMicroID operator.

    Passwords are represented only by an already-computed password hash. The
    domain entity never accepts or exposes a plaintext password.
    """

    username: str
    password_hash: str
    role: UserRole
    id: UUID = field(default_factory=uuid4)
    is_active: bool = True
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        normalized = self.username.strip().lower()
        if not 3 <= len(normalized) <= 100:
            raise ValueError("username must contain between 3 and 100 characters")
        if not self.password_hash.strip():
            raise ValueError("password_hash cannot be empty")
        self.username = normalized

    def deactivate(self) -> None:
        self.is_active = False
        self.updated_at = _utcnow()

    def activate(self) -> None:
        self.is_active = True
        self.updated_at = _utcnow()

    def change_role(self, role: UserRole) -> None:
        self.role = role
        self.updated_at = _utcnow()

    def replace_password_hash(self, password_hash: str) -> None:
        if not password_hash.strip():
            raise ValueError("password_hash cannot be empty")
        self.password_hash = password_hash
        self.updated_at = _utcnow()
