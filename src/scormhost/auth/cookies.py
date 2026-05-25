from __future__ import annotations

from fastapi import Response

from scormhost.config import HostSettings


def set_auth_cookies(
    response: Response,
    settings: HostSettings,
    *,
    access_token: str,
    refresh_token: str,
) -> None:
    max_age_access = settings.access_token_expire_minutes * 60
    max_age_refresh = settings.refresh_token_expire_days * 24 * 60 * 60
    response.set_cookie(
        settings.access_cookie_name,
        access_token,
        max_age=max_age_access,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        settings.refresh_cookie_name,
        refresh_token,
        max_age=max_age_refresh,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_auth_cookies(response: Response, settings: HostSettings) -> None:
    response.delete_cookie(
        settings.access_cookie_name,
        path="/",
        secure=settings.cookie_secure,
        samesite="lax",
    )
    response.delete_cookie(
        settings.refresh_cookie_name,
        path="/",
        secure=settings.cookie_secure,
        samesite="lax",
    )
