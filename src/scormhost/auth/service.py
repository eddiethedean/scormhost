from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from scormhost.auth.schemas import RegisterRequest
from scormhost.auth.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    refresh_token_expires_at,
    verify_password,
)
from scormhost.config import HostSettings
from scormhost.db.models import RefreshToken, User, UserRole


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username.lower()))


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at.desc())))


def register_user(
    db: Session,
    settings: HostSettings,
    payload: RegisterRequest,
) -> User:
    if not settings.allow_registration:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Registration is disabled",
        )

    email = payload.email.lower()
    username = payload.username.lower()

    if get_user_by_email(db, email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    if get_user_by_username(db, username):
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already taken")

    user_count = db.scalar(select(func.count()).select_from(User)) or 0
    role = UserRole.learner
    if user_count == 0:
        role = UserRole.admin
    elif settings.bootstrap_admin_email and email == settings.bootstrap_admin_email.lower():
        role = UserRole.admin

    user = User(
        email=email,
        username=username,
        hashed_password=hash_password(payload.password),
        display_name=payload.display_name.strip(),
        role=role,
    )
    db.add(user)
    db.flush()
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = get_user_by_email(db, email.lower())
    if user is None or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is disabled")
    return user


def issue_tokens(
    db: Session,
    settings: HostSettings,
    user: User,
    *,
    user_agent: str | None = None,
) -> tuple[str, str]:
    access = create_access_token(
        settings,
        user_id=user.id,
        email=user.email,
        role=user.role.value,
    )
    raw_refresh = new_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh),
            expires_at=refresh_token_expires_at(settings),
            user_agent=user_agent,
        ),
    )
    db.flush()
    return access, raw_refresh


def rotate_refresh_token(
    db: Session,
    settings: HostSettings,
    raw_token: str,
    *,
    user_agent: str | None = None,
) -> tuple[User, str, str]:
    token_hash = hash_refresh_token(raw_token)
    record = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash),
    )
    if record is None or record.revoked_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    now = datetime.now(timezone.utc)
    expires = record.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token expired")

    user = record.user
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is disabled")

    record.revoked_at = now
    return user, *issue_tokens(db, settings, user, user_agent=user_agent)


def revoke_refresh_token(db: Session, raw_token: str) -> None:
    token_hash = hash_refresh_token(raw_token)
    record = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash),
    )
    if record is not None and record.revoked_at is None:
        record.revoked_at = datetime.now(timezone.utc)


def change_password(
    db: Session,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    if not verify_password(current_password, user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is wrong")
    user.hashed_password = hash_password(new_password)


def admin_update_user(
    db: Session,
    user: User,
    *,
    display_name: str | None,
    role: UserRole | None,
    is_active: bool | None,
) -> User:
    if display_name is not None:
        user.display_name = display_name.strip()
    if role is not None:
        user.role = role
    if is_active is not None:
        user.is_active = is_active
    db.flush()
    return user


def delete_user(db: Session, user: User) -> None:
    db.delete(user)
