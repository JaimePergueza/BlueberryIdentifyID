import hashlib
import secrets

from blueberry_microid.application.ports.session_token_service import (
    IssuedSessionToken,
    SessionTokenServicePort,
)


class SecureSessionTokenService(SessionTokenServicePort):
    """Issues 256-bit URL-safe tokens and stores only their SHA-256 digest."""

    def issue(self) -> IssuedSessionToken:
        raw_token = secrets.token_urlsafe(32)
        return IssuedSessionToken(
            raw_token=raw_token,
            token_hash=self.hash_token(raw_token),
        )

    def hash_token(self, raw_token: str) -> str:
        if not raw_token:
            raise ValueError("session token cannot be empty")
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
