from __future__ import annotations

import zipfile
from pathlib import Path as PathLib
from typing import Annotated, Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from starlette.responses import Response

from scormhost.auth.dependencies import (
    CurrentUser,
    LearningActor,
    RequireInstructor,
    get_current_user_optional,
    get_settings,
    resolve_learning_actor,
)
from scormhost.auth.guest import apply_guest_cookie_if_needed
from scormhost.auth.urls import login_url, safe_next_path
from scormhost.auth.router import router as auth_router
from scormhost.config import HostSettings
from scormhost.db.models import User, UserRole
from scormhost.manifest import is_scorm_2004_schema
from scormhost.packages import can_delete_package, delete_package, extract_scorm_zip
from scormhost.paths import (
    InvalidPackageIdError,
    PathTraversalError,
    is_safe_launch_href,
    safe_content_path,
)
from scormhost.storage import PackageStore, SessionStore
from scormhost.templates import catalog_page, launcher_page, package_detail_page

STATIC_DIR = PathLib(__file__).resolve().parent / "static"


class CmiPayload(BaseModel):
    elements: dict[str, str] = {}


_MAX_CMI_BODY_BYTES = 256 * 1024


def _resolve_launch_href(launch: str, launches: list[dict[str, Any]]) -> str:
    known = {
        item["href"] for item in launches if is_safe_launch_href(item.get("href", ""))
    }
    if known:
        if launch in known:
            return launch
        return launches[0]["href"]
    if launches:
        first = launches[0]["href"]
        if is_safe_launch_href(first):
            return first
    if is_safe_launch_href(launch):
        return launch
    return "index.html"


def _request_next_path(request: Request) -> str:
    path = request.url.path
    if request.url.query:
        path = f"{path}?{request.url.query}"
    return safe_next_path(path)


def build_router(settings: HostSettings) -> APIRouter:
    router = APIRouter()
    packages = PackageStore(settings)
    sessions = SessionStore(settings)
    prefix = settings.api_prefix

    def url(path: str) -> str:
        if not prefix:
            return path
        return f"{prefix}{path}"

    def _redirect_login(request: Request) -> RedirectResponse:
        return RedirectResponse(
            url=login_url(_request_next_path(request), url=url),
            status_code=302,
        )

    router.include_router(auth_router)

    @router.get("/", response_class=HTMLResponse, response_model=None)
    async def catalog(
        request: Request,
        settings: Annotated[HostSettings, Depends(get_settings)],
        user: Annotated[User | None, Depends(get_current_user_optional)],
    ) -> Response:
        if settings.require_auth and user is None:
            return _redirect_login(request)
        actor = resolve_learning_actor(settings, user, guest_id=None, request=request)

        records = packages.list_packages()
        pkg_rows = []
        for record in records:
            row = record.to_dict()
            try:
                meta = packages.load_meta(record.id)
                row["can_delete"] = can_delete_package(
                    meta,
                    actor.user_id,
                    actor.can_delete_any_package,
                )
            except FileNotFoundError:
                row["can_delete"] = False
            pkg_rows.append(row)

        user_label = None
        if actor.user:
            user_label = f"{actor.display_name} ({actor.user.role.value})"

        body = catalog_page(
            settings.title,
            pkg_rows,
            user_label=user_label,
            can_upload=actor.can_upload,
            show_admin=actor.can_manage_users,
            show_delete=bool(actor.user),
            is_logged_in=actor.user is not None,
            url=url,
        )
        response = HTMLResponse(body)
        apply_guest_cookie_if_needed(response, request, settings, user)
        return response

    @router.get(
        "/packages/{package_id}", response_class=HTMLResponse, response_model=None
    )
    async def package_detail(
        request: Request,
        package_id: str,
        settings: Annotated[HostSettings, Depends(get_settings)],
        user: Annotated[User | None, Depends(get_current_user_optional)],
    ) -> Response:
        if settings.require_auth and user is None:
            return _redirect_login(request)
        actor = resolve_learning_actor(settings, user, guest_id=None, request=request)
        try:
            meta = packages.load_meta(package_id)
        except (FileNotFoundError, ValueError):
            raise HTTPException(404, "Package not found") from None
        manifest = meta["manifest"]
        launches = manifest.get("launches", [])
        if len(launches) <= 1:
            launch = launches[0]["href"] if launches else "index.html"
            launch = _resolve_launch_href(launch, launches)
            return RedirectResponse(
                url=url(
                    f"/launch/{package_id}?launch={quote(launch, safe='')}",
                ),
                status_code=302,
            )
        user_label = actor.display_name if actor.user else None
        response = HTMLResponse(
            package_detail_page(
                manifest.get("title", package_id),
                package_id,
                launches,
                user_label=user_label,
                url=url,
            ),
        )
        apply_guest_cookie_if_needed(response, request, settings, user)
        return response

    @router.get(
        "/launch/{package_id}", response_class=HTMLResponse, response_model=None
    )
    async def launch_package(
        request: Request,
        package_id: str,
        settings: Annotated[HostSettings, Depends(get_settings)],
        user: Annotated[User | None, Depends(get_current_user_optional)],
        launch: str = Query(default="index.html"),
    ) -> Response:
        if settings.require_auth and user is None:
            return _redirect_login(request)
        actor = resolve_learning_actor(settings, user, guest_id=None, request=request)
        try:
            meta = packages.load_meta(package_id)
        except (FileNotFoundError, ValueError):
            raise HTTPException(404, "Package not found") from None

        manifest = meta["manifest"]
        launches = manifest.get("launches", [])
        launch_href = _resolve_launch_href(launch, launches)
        if not is_safe_launch_href(launch_href):
            raise HTTPException(400, "Invalid launch path")

        is_2004 = is_scorm_2004_schema(manifest.get("schema_version", ""))
        content_url = url(
            f"/content/{package_id}/{launch_href.lstrip('/')}",
        )
        cmi_url = url(
            f"/api/scorm/{package_id}/cmi?launch={quote(launch_href, safe='')}",
        )
        scorm_config: dict[str, Any] = {
            "learnerId": actor.learner_id,
            "learnerName": actor.display_name,
            "contentUrl": content_url,
            "cmiUrl": cmi_url,
            "progressIsAccount": actor.progress_is_account,
        }
        api_script = url(
            "/static/scorm2004-api.js" if is_2004 else "/static/scorm12-api.js",
        )
        response = HTMLResponse(
            launcher_page(
                package_title=manifest.get("title", package_id),
                package_id=package_id,
                launch_href=launch_href,
                is_scorm_2004=is_2004,
                scorm_config=scorm_config,
                api_script=api_script,
                is_logged_in=actor.user is not None,
                login_href=login_url(_request_next_path(request), url=url),
                url=url,
            ),
        )
        apply_guest_cookie_if_needed(response, request, settings, user)
        return response

    @router.get("/content/{package_id}/{rel_path:path}")
    async def serve_content(
        package_id: str,
        rel_path: str,
        settings: Annotated[HostSettings, Depends(get_settings)],
        user: Annotated[User | None, Depends(get_current_user_optional)],
    ) -> FileResponse:
        if settings.require_auth and user is None:
            raise HTTPException(401, "Not authenticated")
        try:
            root = packages.package_root(package_id)
            if not root.is_dir():
                raise FileNotFoundError
            file_path = safe_content_path(root, rel_path)
        except (FileNotFoundError, PathTraversalError, ValueError) as exc:
            raise HTTPException(404, "Not found") from exc
        if not file_path.is_file():
            raise HTTPException(404, "Not found")
        return FileResponse(file_path)

    @router.get("/static/{asset_name}")
    async def serve_static(asset_name: str) -> FileResponse:
        if asset_name not in ("scorm12-api.js", "scorm2004-api.js"):
            raise HTTPException(404, "Not found")
        path = STATIC_DIR / asset_name
        return FileResponse(path, media_type="application/javascript")

    @router.get("/api/packages")
    async def list_packages_api() -> JSONResponse:
        return JSONResponse([r.to_dict() for r in packages.list_packages()])

    @router.post("/api/packages")
    async def upload_package(
        user: RequireInstructor,
        settings: Annotated[HostSettings, Depends(get_settings)],
        file: UploadFile = File(...),
        package_id: str | None = Query(default=None),
    ) -> JSONResponse:
        if not settings.allow_upload:
            raise HTTPException(403, "Uploads are disabled on this server")
        if not file.filename or not file.filename.lower().endswith(".zip"):
            raise HTTPException(400, "Upload must be a .zip file")

        body = await file.read()
        if len(body) > settings.max_upload_bytes:
            raise HTTPException(413, "Package exceeds size limit")

        try:
            pid = extract_scorm_zip(
                packages,
                body,
                file.filename,
                preferred_id=package_id,
                uploaded_by_id=user.id,
            )
        except (ValueError, InvalidPackageIdError) as exc:
            raise HTTPException(400, str(exc)) from exc
        except zipfile.BadZipFile as exc:
            raise HTTPException(400, "Invalid zip file") from exc

        meta = packages.load_meta(pid)
        return JSONResponse(
            {
                "id": pid,
                "launch_url": url(f"/launch/{pid}"),
                "manifest": meta["manifest"],
            },
            status_code=201,
        )

    @router.delete("/api/packages/{package_id}")
    async def remove_package(
        package_id: str,
        user: CurrentUser,
    ) -> JSONResponse:
        try:
            meta = packages.load_meta(package_id)
        except (FileNotFoundError, ValueError):
            raise HTTPException(404, "Package not found") from None
        is_admin = user.role == UserRole.admin
        if not can_delete_package(meta, user.id, is_admin):
            raise HTTPException(403, "Cannot delete this package")
        delete_package(packages, package_id)
        return JSONResponse({"deleted": package_id})

    @router.get("/api/scorm/{package_id}/cmi")
    async def get_cmi(
        request: Request,
        package_id: str,
        actor: LearningActor,
        settings: Annotated[HostSettings, Depends(get_settings)],
        launch: str = Query(default="index.html"),
    ) -> JSONResponse:
        try:
            packages.load_meta(package_id)
        except (FileNotFoundError, ValueError):
            raise HTTPException(404, "Package not found") from None
        try:
            elements = sessions.load_cmi(package_id, actor.learner_id, launch)
        except ValueError:
            raise HTTPException(404, "Package not found") from None
        response = JSONResponse({"elements": elements})
        apply_guest_cookie_if_needed(
            response,
            request,
            settings,
            actor.user,
        )
        return response

    @router.put("/api/scorm/{package_id}/cmi")
    async def put_cmi(
        request: Request,
        package_id: str,
        payload: CmiPayload,
        actor: LearningActor,
        settings: Annotated[HostSettings, Depends(get_settings)],
        launch: str = Query(default="index.html"),
    ) -> JSONResponse:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > _MAX_CMI_BODY_BYTES:
                    raise HTTPException(413, "CMI payload too large")
            except ValueError:
                pass
        if not payload.elements:
            raise HTTPException(400, "elements must not be empty")
        try:
            packages.load_meta(package_id)
        except (FileNotFoundError, ValueError):
            raise HTTPException(404, "Package not found") from None
        try:
            existing = sessions.load_cmi(package_id, actor.learner_id, launch)
        except ValueError:
            raise HTTPException(404, "Package not found") from None
        merged = {**existing, **payload.elements}
        try:
            sessions.save_cmi(
                package_id,
                actor.learner_id,
                launch,
                merged,
            )
        except ValueError:
            raise HTTPException(404, "Package not found") from None
        response = JSONResponse({"ok": True})
        apply_guest_cookie_if_needed(
            response,
            request,
            settings,
            actor.user,
        )
        return response

    @router.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return router
