from __future__ import annotations

import re
import secrets

from fastapi import Request, Response

from scormhost.config import HostSettings
from scormhost.db.models import User

_GUEST_ID_RE = re.compile(r"^guest-[A-Za-z0-9_-]{12,}$")


def valid_guest_learner_id(request: Request, settings: HostSettings) -> str | None:
    """Return server-issued guest id from cookie, or None if missing/invalid."""
    raw = request.cookies.get(settings.guest_cookie_name)
    if not raw or not _GUEST_ID_RE.match(raw):
        return None
    return raw


def new_guest_learner_id() -> str:
    return f"guest-{secrets.token_urlsafe(12)}"


def ensure_guest_learner_id(request: Request, settings: HostSettings) -> str:
    """Stable guest id for this request; persisted via cookie on the response."""
    existing = valid_guest_learner_id(request, settings)
    if existing:
        return existing
    pending = getattr(request.state, "scormhost_guest_id", None)
    if pending:
        return pending
    guest_id = new_guest_learner_id()
    request.state.scormhost_guest_id = guest_id
    return guest_id


def apply_guest_cookie_if_needed(
    response: Response,
    request: Request,
    settings: HostSettings,
    user: User | None,
) -> None:
    """Assign a stable anonymous learner id in the browser (progress on this device)."""
    if user is not None:
        return
    if valid_guest_learner_id(request, settings):
        return
    guest_id = getattr(request.state, "scormhost_guest_id", None) or new_guest_learner_id()
    response.set_cookie(
        settings.guest_cookie_name,
        guest_id,
        max_age=60 * 60 * 24 * 365,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
