from pwdlib import PasswordHash

from blueberry_microid.application.ports.password_hasher import PasswordHasherPort


class PwdlibPasswordHasher(PasswordHasherPort):
    """Argon2 password hashing through pwdlib's recommended configuration."""

    def __init__(self) -> None:
        self._password_hash = PasswordHash.recommended()

    def hash(self, password: str) -> str:
        if len(password) < 12:
            raise ValueError("password must contain at least 12 characters")
        return self._password_hash.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            return self._password_hash.verify(password, password_hash)
        except (ValueError, TypeError):
            return False
