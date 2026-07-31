from abc import ABC, abstractmethod


class PasswordHasherPort(ABC):
    """One-way password hashing independent from the concrete library."""

    @abstractmethod
    def hash(self, password: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def verify(self, password: str, password_hash: str) -> bool:
        raise NotImplementedError
