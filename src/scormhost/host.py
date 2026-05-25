from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from scormhost.config import HostSettings
from scormhost.router import build_router


class ScormHost:
    """Mount SCORM hosting routes onto a FastAPI application."""

    def __init__(
        self,
        settings: HostSettings | None = None,
        *,
        data_dir: str | Path | None = None,
        title: str | None = None,
        allow_upload: bool | None = None,
        require_auth: bool | None = None,
        secret_key: str | None = None,
    ) -> None:
        if settings is None:
            if data_dir is not None:
                settings = HostSettings.from_env(Path(data_dir))
            else:
                settings = HostSettings.from_env()
            overrides: dict[str, object] = {}
            if title is not None:
                overrides["title"] = title
            if allow_upload is not None:
                overrides["allow_upload"] = allow_upload
            if require_auth is not None:
                overrides["require_auth"] = require_auth
            if secret_key is not None:
                overrides["secret_key"] = secret_key
            if overrides:
                settings = HostSettings(
                    data_dir=settings.data_dir,
                    title=str(overrides.get("title", settings.title)),
                    allow_upload=bool(
                        overrides.get("allow_upload", settings.allow_upload),
                    ),
                    max_upload_bytes=settings.max_upload_bytes,
                    default_learner_id=settings.default_learner_id,
                    api_prefix=settings.api_prefix,
                    database_url=settings.database_url,
                    secret_key=str(overrides.get("secret_key", settings.secret_key)),
                    jwt_algorithm=settings.jwt_algorithm,
                    access_token_expire_minutes=settings.access_token_expire_minutes,
                    refresh_token_expire_days=settings.refresh_token_expire_days,
                    allow_registration=settings.allow_registration,
                    require_auth=bool(
                        overrides.get("require_auth", settings.require_auth),
                    ),
                    cookie_secure=settings.cookie_secure,
                    auto_migrate=settings.auto_migrate,
                    bootstrap_admin_email=settings.bootstrap_admin_email,
                )
        elif any(
            x is not None for x in (title, allow_upload, require_auth, secret_key)
        ):
            settings = HostSettings(
                data_dir=settings.data_dir,
                title=title or settings.title,
                allow_upload=allow_upload
                if allow_upload is not None
                else settings.allow_upload,
                max_upload_bytes=settings.max_upload_bytes,
                default_learner_id=settings.default_learner_id,
                api_prefix=settings.api_prefix,
                database_url=settings.database_url,
                secret_key=secret_key or settings.secret_key,
                jwt_algorithm=settings.jwt_algorithm,
                access_token_expire_minutes=settings.access_token_expire_minutes,
                refresh_token_expire_days=settings.refresh_token_expire_days,
                allow_registration=settings.allow_registration,
                require_auth=require_auth
                if require_auth is not None
                else settings.require_auth,
                cookie_secure=settings.cookie_secure,
                auto_migrate=settings.auto_migrate,
                bootstrap_admin_email=settings.bootstrap_admin_email,
            )

        self.settings = settings
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings.packages_dir.mkdir(parents=True, exist_ok=True)
        self.settings.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._router = build_router(settings)

    def mount(self, app: FastAPI) -> None:
        if not hasattr(app.state, "settings"):
            app.state.settings = self.settings
        app.include_router(self._router)

    @property
    def router(self):
        return self._router
