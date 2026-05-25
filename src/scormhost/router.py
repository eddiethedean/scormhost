from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

from scormhost.config import HostSettings
from scormhost.packages import delete_package, extract_scorm_zip
from scormhost.paths import PathTraversalError, safe_content_path
from scormhost.storage import PackageStore, SessionStore
from scormhost.templates import catalog_page, launcher_page, package_detail_page

STATIC_DIR = Path(__file__).resolve().parent / "static"


class CmiPayload(BaseModel):
    elements: dict[str, str] = {}


def build_router(settings: HostSettings) -> APIRouter:
    router = APIRouter()
    packages = PackageStore(settings)
    sessions = SessionStore(settings)
    prefix = settings.api_prefix

    def url(path: str) -> str:
        if not prefix:
            return path
        return f"{prefix}{path}"

    @router.get("/", response_class=HTMLResponse)
    async def catalog() -> str:
        records = packages.list_packages()
        return catalog_page(
            settings.title,
            [r.to_dict() for r in records],
            settings.allow_upload,
        )

    @router.get("/packages/{package_id}", response_class=HTMLResponse)
    async def package_detail(package_id: str) -> str:
        try:
            meta = packages.load_meta(package_id)
        except FileNotFoundError:
            raise HTTPException(404, "Package not found") from None
        manifest = meta["manifest"]
        launches = manifest.get("launches", [])
        if len(launches) <= 1:
            launch = launches[0]["href"] if launches else "index.html"
            return RedirectResponse(
                url=f"/launch/{package_id}?launch={quote(launch, safe='')}",
                status_code=302,
            )
        return package_detail_page(
            manifest.get("title", package_id),
            package_id,
            launches,
        )

    @router.get("/launch/{package_id}", response_class=HTMLResponse)
    async def launch_package(
        package_id: str,
        launch: str = Query(default="index.html"),
        learner_id: str | None = Query(default=None),
    ) -> str:
        try:
            meta = packages.load_meta(package_id)
        except FileNotFoundError:
            raise HTTPException(404, "Package not found") from None

        manifest = meta["manifest"]
        launches = manifest.get("launches", [])
        launch_href = launch
        known = {item["href"] for item in launches}
        if known and launch_href not in known:
            launch_href = launches[0]["href"]

        learner = learner_id or settings.default_learner_id
        is_2004 = "2004" in manifest.get("schema_version", "")
        content_url = url(
            f"/content/{package_id}/{launch_href.lstrip('/')}",
        )
        cmi_url = url(
            f"/api/scorm/{package_id}/cmi"
            f"?learner_id={quote(learner)}&launch={quote(launch_href, safe='')}",
        )
        scorm_config: dict[str, Any] = {
            "learnerId": learner,
            "learnerName": learner,
            "contentUrl": content_url,
            "cmiUrl": cmi_url,
        }
        api_script = url(
            "/static/scorm2004-api.js" if is_2004 else "/static/scorm12-api.js",
        )
        return launcher_page(
            package_title=manifest.get("title", package_id),
            package_id=package_id,
            launch_href=launch_href,
            is_scorm_2004=is_2004,
            scorm_config=scorm_config,
            api_script=api_script,
        )

    @router.get("/content/{package_id}/{rel_path:path}")
    async def serve_content(package_id: str, rel_path: str) -> FileResponse:
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
        return JSONResponse(
            [r.to_dict() for r in packages.list_packages()],
        )

    @router.post("/api/packages")
    async def upload_package(
        file: UploadFile = File(...),
        package_id: str | None = Query(default=None),
    ) -> JSONResponse:
        if not settings.allow_upload:
            raise HTTPException(403, "Uploads disabled")
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
            )
        except ValueError as exc:
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
    async def remove_package(package_id: str) -> JSONResponse:
        try:
            packages.load_meta(package_id)
        except FileNotFoundError:
            raise HTTPException(404, "Package not found") from None
        delete_package(packages, package_id)
        return JSONResponse({"deleted": package_id})

    @router.get("/api/scorm/{package_id}/cmi")
    async def get_cmi(
        package_id: str,
        learner_id: str = Query(...),
        launch: str = Query(default="index.html"),
    ) -> JSONResponse:
        elements = sessions.load_cmi(package_id, learner_id, launch)
        return JSONResponse({"elements": elements})

    @router.put("/api/scorm/{package_id}/cmi")
    async def put_cmi(
        package_id: str,
        payload: CmiPayload,
        learner_id: str = Query(...),
        launch: str = Query(default="index.html"),
    ) -> JSONResponse:
        try:
            packages.load_meta(package_id)
        except FileNotFoundError:
            raise HTTPException(404, "Package not found") from None
        sessions.save_cmi(
            package_id,
            learner_id,
            launch,
            payload.elements,
        )
        return JSONResponse({"ok": True})

    @router.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return router
