from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from blueberry_microid.domain.enums.user_role import UserRole


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LoginRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    token_type: str
    expires_at: datetime
    user: UserRead


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=12, max_length=256)
    role: UserRole

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not 3 <= len(normalized) <= 100:
            raise ValueError("username must contain between 3 and 100 non-space characters")
        return normalized

    @field_validator("password")
    @classmethod
    def reject_blank_password(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("password cannot contain only whitespace")
        return value


class UserUpdate(BaseModel):
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=12, max_length=256)

    @field_validator("password")
    @classmethod
    def reject_blank_password(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            raise ValueError("password cannot contain only whitespace")
        return value

    @model_validator(mode="after")
    def require_at_least_one_change(self) -> "UserUpdate":
        if self.role is None and self.is_active is None and self.password is None:
            raise ValueError("at least one user field must be provided")
        return self


class UserListRead(BaseModel):
    users: list[UserRead]


class LogoutRead(BaseModel):
    message: str
