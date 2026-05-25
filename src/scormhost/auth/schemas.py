from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from scormhost.db.models import UserRole


class UserPublic(BaseModel):
    id: int
    email: EmailStr
    username: str
    display_name: str
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class AdminUpdateUserRequest(BaseModel):
    display_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
