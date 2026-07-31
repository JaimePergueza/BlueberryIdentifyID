from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IssuedSessionToken:
    raw_token: str
    token_hash: str


class SessionTokenServicePort(ABC):
    """Creates high-entropy bearer tokens and irreversible lookup digests."""

    @abstractmethod
    def issue(self) -> IssuedSessionToken:
        raise NotImplementedError

    @abstractmethod
    def hash_token(self, raw_token: str) -> str:
        raise NotImplementedError
