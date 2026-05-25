from __future__ import annotations

import secrets

from fastapi import Request, Response

from scormhost.config import HostSettings
from scormhost.db.models import User


def guest_learner_id(request: Request, settings: HostSettings) -> str | None:
    return request.cookies.get(settings.guest_cookie_name)


def new_guest_learner_id() -> str:
    return f"guest-{secrets.token_urlsafe(12)}"


def apply_guest_cookie_if_needed(
    response: Response,
    request: Request,
    settings: HostSettings,
    user: User | None,
) -> None:
    """Assign a stable anonymous learner id in the browser (progress on this device)."""
    if user is not None:
        return
    if guest_learner_id(request, settings):
        return
    response.set_cookie(
        settings.guest_cookie_name,
        new_guest_learner_id(),
        max_age=60 * 60 * 24 * 365,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
