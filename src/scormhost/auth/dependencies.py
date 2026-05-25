from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from scormhost.auth.guest import ensure_guest_learner_id, valid_guest_learner_id
from scormhost.auth.security import decode_access_token
from scormhost.config import HostSettings
from scormhost.db.models import User, UserRole
from scormhost.db.session import get_db

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Actor:
    """Resolved identity for SCORM runtime (learner progress + optional staff user)."""

    user: User | None
    learner_id: str
    display_name: str
    can_upload: bool
    can_manage_users: bool
    can_delete_any_package: bool
    progress_is_account: bool

    @property
    def user_id(self) -> int | None:
        return self.user.id if self.user else None


def get_settings(request: Request) -> HostSettings:
    return request.app.state.settings


def _token_from_request(
    request: Request,
    settings: HostSettings,
    credentials: HTTPAuthorizationCredentials | None,
) -> str | None:
    if credentials is not None and credentials.scheme.lower() == "bearer":
        return credentials.credentials
    return request.cookies.get(settings.access_cookie_name)


def get_current_user_optional(
    request: Request,
    settings: Annotated[HostSettings, Depends(get_settings)],
    db: Annotated[Session, Depends(get_db)],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer),
    ] = None,
) -> User | None:
    token = _token_from_request(request, settings, credentials)
    if not token:
        return None

    try:
        payload = decode_access_token(settings, token)
    except jwt.PyJWTError:
        return None

    sub = payload.get("sub")
    if sub is None:
        return None
    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        return None

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return user


def get_current_user(
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> User:
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def resolve_learning_actor(
    settings: HostSettings,
    user: User | None,
    *,
    guest_id: str | None,
    request: Request | None = None,
) -> Actor:
    """Taking a course: logged-in users save to their account; guests use browser cookie."""
    if user is not None:
        can_upload = user.role in (UserRole.instructor, UserRole.admin)
        return Actor(
            user=user,
            learner_id=str(user.id),
            display_name=user.display_name,
            can_upload=can_upload and settings.allow_upload,
            can_manage_users=user.role == UserRole.admin,
            can_delete_any_package=user.role == UserRole.admin,
            progress_is_account=True,
        )

    if request is not None:
        learner = ensure_guest_learner_id(request, settings)
    elif guest_id:
        learner = guest_id
    else:
        learner = f"guest-{secrets.token_urlsafe(12)}"
    return Actor(
        user=None,
        learner_id=learner,
        display_name="Guest",
        can_upload=False,
        can_manage_users=False,
        can_delete_any_package=False,
        progress_is_account=False,
    )


def get_learning_actor(
    request: Request,
    settings: Annotated[HostSettings, Depends(get_settings)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> Actor:
    if settings.require_auth and user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Log in to take courses and save progress",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return resolve_learning_actor(settings, user, guest_id=None, request=request)


def require_roles(*roles: UserRole):
    """Course management (upload, admin) — must be signed in."""

    def checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Insufficient permissions",
            )
        return user

    return checker


RequireAdmin = Annotated[User, Depends(require_roles(UserRole.admin))]
RequireInstructor = Annotated[
    User,
    Depends(require_roles(UserRole.instructor, UserRole.admin)),
]

LearningActor = Annotated[Actor, Depends(get_learning_actor)]
CurrentUser = Annotated[User, Depends(get_current_user)]
