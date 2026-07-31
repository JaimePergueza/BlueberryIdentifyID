from enum import Enum


class UserRole(str, Enum):
    """Authorization roles supported by the demonstrable MVP."""

    ADMIN = "admin"
    SPECIALIST = "specialist"
