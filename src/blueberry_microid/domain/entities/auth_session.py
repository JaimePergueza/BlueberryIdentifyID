from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AuthSession:
    """Revocable bearer session stored only through a token hash."""

    user_id: UUID
    token_hash: str
    expires_at: datetime
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_utcnow)
    revoked_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if len(self.token_hash) != 64:
            raise ValueError("token_hash must be a SHA-256 hexadecimal digest")
        if self.expires_at.tzinfo is None:
            raise ValueError("expires_at must be timezone-aware")

    def revoke(self, at: Optional[datetime] = None) -> None:
        self.revoked_at = at or _utcnow()

    def is_valid(self, now: Optional[datetime] = None) -> bool:
        current = now or _utcnow()
        return self.revoked_at is None and current < self.expires_at
