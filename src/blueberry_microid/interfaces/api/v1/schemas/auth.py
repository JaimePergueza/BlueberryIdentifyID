from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

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


class UserUpdate(BaseModel):
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=12, max_length=256)

    @model_validator(mode="after")
    def require_at_least_one_change(self) -> "UserUpdate":
        if self.role is None and self.is_active is None and self.password is None:
            raise ValueError("at least one user field must be provided")
        return self


class UserListRead(BaseModel):
    users: list[UserRead]


class LogoutRead(BaseModel):
    message: str
