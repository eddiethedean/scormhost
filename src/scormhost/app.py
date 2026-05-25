from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from scormhost.config import HostSettings
from scormhost.db.session import init_engine
from scormhost.host import ScormHost
from scormhost.migrate import run_migrations


@asynccontextmanager
async def _lifespan(app: FastAPI):
    settings: HostSettings = app.state.settings
    init_engine(settings)
    if settings.auto_migrate:
        run_migrations(settings.database_url)
    yield


def create_scorm_app(
    *,
    data_dir: str | Path = "./data",
    title: str = "SCORM Host",
    allow_upload: bool = True,
    default_learner_id: str = "demo-learner",
    require_auth: bool = False,
    secret_key: str | None = None,
    database_url: str | None = None,
    allow_registration: bool = True,
    auto_migrate: bool = True,
    api_prefix: str | None = None,
) -> FastAPI:
    """
    Create a FastAPI app that hosts SCORM 1.2 / 2004 ZIP packages.

    Courses are public by default (``require_auth=False``). Learners may sign in
    to persist progress to an account; instructors/admins sign in to upload packages.

    Deploy to FastAPI Cloud with ``fastapi deploy``. Set ``SCORMHOST_DATA_DIR`` and
    ``SCORMHOST_SECRET_KEY`` in production.
    """
    base = HostSettings.from_env(Path(data_dir))
    settings = HostSettings(
        data_dir=base.data_dir,
        title=title,
        allow_upload=allow_upload,
        default_learner_id=default_learner_id,
        api_prefix=api_prefix if api_prefix is not None else base.api_prefix,
        database_url=database_url or base.database_url,
        secret_key=secret_key or base.secret_key,
        jwt_algorithm=base.jwt_algorithm,
        access_token_expire_minutes=base.access_token_expire_minutes,
        refresh_token_expire_days=base.refresh_token_expire_days,
        allow_registration=allow_registration,
        require_auth=require_auth,
        cookie_secure=base.cookie_secure,
        auto_migrate=auto_migrate,
        bootstrap_admin_email=base.bootstrap_admin_email,
        max_upload_bytes=base.max_upload_bytes,
    )
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.packages_dir.mkdir(parents=True, exist_ok=True)
    settings.sessions_dir.mkdir(parents=True, exist_ok=True)

    app = FastAPI(
        title=title,
        description="Public SCORM host with optional accounts for progress and management",
        version="0.1.0",
        lifespan=_lifespan,
    )
    app.state.settings = settings
    ScormHost(settings).mount(app)
    return app
