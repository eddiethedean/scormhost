from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from starlette.responses import Response as StarletteResponse

from scormhost.auth.cookies import clear_auth_cookies, set_auth_cookies
from scormhost.auth.dependencies import (
    CurrentUser,
    RequireAdmin,
    get_settings,
)
from scormhost.auth.schemas import (
    AdminUpdateUserRequest,
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserPublic,
)
from scormhost.auth.service import (
    admin_update_user,
    authenticate_user,
    change_password,
    count_active_admins,
    delete_user,
    get_user_by_id,
    issue_tokens,
    list_users,
    register_user,
    revoke_refresh_token,
    rotate_refresh_token,
)
from scormhost.auth.urls import safe_next_path
from scormhost.config import HostSettings
from scormhost.db.models import UserRole
from scormhost.db.session import get_db
from scormhost.templates import admin_users_page, auth_page

router = APIRouter(tags=["auth"])


def _token_response(
    settings: HostSettings,
    user,
    access: str,
    refresh: str,
    *,
    set_cookies: bool,
) -> JSONResponse:
    body = TokenResponse(
        access_token=access,
        user=UserPublic.model_validate(user),
    )
    response = JSONResponse(body.model_dump(mode="json"))
    if set_cookies:
        set_auth_cookies(response, settings, access_token=access, refresh_token=refresh)
    return response


def _url_for(settings: HostSettings):
    prefix = settings.api_prefix

    def url(path: str) -> str:
        if not prefix:
            return path
        return f"{prefix}{path}"

    return url


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    settings: Annotated[HostSettings, Depends(get_settings)],
) -> str:
    return auth_page(
        title=settings.title,
        mode="login",
        allow_registration=settings.allow_registration,
        error=request.query_params.get("error"),
        next_url=safe_next_path(request.query_params.get("next")),
        url=_url_for(settings),
    )


@router.get("/register", response_class=HTMLResponse, response_model=None)
async def register_page(
    request: Request,
    settings: Annotated[HostSettings, Depends(get_settings)],
) -> StarletteResponse:
    url = _url_for(settings)
    if not settings.allow_registration:
        return RedirectResponse(
            f"{url('/login')}?error=registration+disabled",
            status_code=302,
        )
    return HTMLResponse(
        auth_page(
            title=settings.title,
            mode="register",
            allow_registration=True,
            error=request.query_params.get("error"),
            next_url=safe_next_path(request.query_params.get("next")),
            url=url,
        ),
    )


@router.post("/api/auth/register")
async def api_register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    settings: Annotated[HostSettings, Depends(get_settings)],
    db: Annotated[Session, Depends(get_db)],
) -> JSONResponse:
    user = register_user(db, settings, payload)
    access, refresh = issue_tokens(
        db,
        settings,
        user,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return _token_response(settings, user, access, refresh, set_cookies=True)


@router.post("/api/auth/login")
async def api_login(
    payload: LoginRequest,
    request: Request,
    settings: Annotated[HostSettings, Depends(get_settings)],
    db: Annotated[Session, Depends(get_db)],
) -> JSONResponse:
    user = authenticate_user(db, payload.email, payload.password)
    access, refresh = issue_tokens(
        db,
        settings,
        user,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return _token_response(settings, user, access, refresh, set_cookies=True)


@router.post("/api/auth/refresh")
async def api_refresh(
    request: Request,
    settings: Annotated[HostSettings, Depends(get_settings)],
    db: Annotated[Session, Depends(get_db)],
) -> JSONResponse:
    raw = request.cookies.get(settings.refresh_cookie_name)
    if not raw:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing refresh token")
    user, access, refresh = rotate_refresh_token(
        db,
        settings,
        raw,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return _token_response(settings, user, access, refresh, set_cookies=True)


@router.post("/api/auth/logout")
async def api_logout(
    request: Request,
    settings: Annotated[HostSettings, Depends(get_settings)],
    db: Annotated[Session, Depends(get_db)],
) -> JSONResponse:
    raw = request.cookies.get(settings.refresh_cookie_name)
    if raw:
        revoke_refresh_token(db, raw)
        db.commit()
    response = JSONResponse({"ok": True})
    clear_auth_cookies(response, settings)
    return response


@router.get("/api/auth/me", response_model=UserPublic)
async def api_me(user: CurrentUser) -> UserPublic:
    return UserPublic.model_validate(user)


@router.patch("/api/auth/me/password")
async def api_change_password(
    payload: ChangePasswordRequest,
    user: CurrentUser,
    settings: Annotated[HostSettings, Depends(get_settings)],
    db: Annotated[Session, Depends(get_db)],
) -> JSONResponse:
    change_password(db, user, payload.current_password, payload.new_password)
    db.commit()
    response = JSONResponse({"ok": True})
    clear_auth_cookies(response, settings)
    return response


@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users_html(
    actor: RequireAdmin,
    settings: Annotated[HostSettings, Depends(get_settings)],
) -> str:
    return admin_users_page(url=_url_for(settings))


@router.get("/api/users", response_model=list[UserPublic])
async def api_list_users(
    actor: RequireAdmin,
    db: Annotated[Session, Depends(get_db)],
) -> list[UserPublic]:
    return [UserPublic.model_validate(u) for u in list_users(db)]


@router.get("/api/users/{user_id}", response_model=UserPublic)
async def api_get_user(
    user_id: int,
    actor: RequireAdmin,
    db: Annotated[Session, Depends(get_db)],
) -> UserPublic:
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return UserPublic.model_validate(user)


@router.patch("/api/users/{user_id}", response_model=UserPublic)
async def api_update_user(
    user_id: int,
    payload: AdminUpdateUserRequest,
    actor: RequireAdmin,
    db: Annotated[Session, Depends(get_db)],
) -> UserPublic:
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == actor.id and payload.is_active is False:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot deactivate yourself")
    if user.role == UserRole.admin:
        admins = count_active_admins(db)
        demoting = payload.role is not None and payload.role != UserRole.admin
        deactivating = payload.is_active is False
        if admins <= 1 and (demoting or deactivating):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Cannot remove or deactivate the last admin",
            )
    if (
        user.id == actor.id
        and payload.role is not None
        and payload.role != UserRole.admin
    ):
        if count_active_admins(db) <= 1:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Cannot demote yourself as the only admin",
            )
    admin_update_user(
        db,
        user,
        display_name=payload.display_name,
        role=payload.role,
        is_active=payload.is_active,
    )
    db.commit()
    return UserPublic.model_validate(user)


@router.delete("/api/users/{user_id}")
async def api_delete_user(
    user_id: int,
    actor: RequireAdmin,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, bool]:
    if user_id == actor.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete yourself")
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.role == UserRole.admin and count_active_admins(db) <= 1:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cannot delete the last admin",
        )
    delete_user(db, user)
    db.commit()
    return {"ok": True}
