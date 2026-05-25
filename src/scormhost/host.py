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
    ) -> None:
        if settings is None:
            if data_dir is not None:
                settings = HostSettings(
                    data_dir=Path(data_dir).expanduser().resolve(),
                    title=title or "SCORM Host",
                    allow_upload=True if allow_upload is None else allow_upload,
                )
            else:
                settings = HostSettings.from_env()
                if title is not None:
                    settings = HostSettings(
                        data_dir=settings.data_dir,
                        title=title,
                        allow_upload=(
                            settings.allow_upload
                            if allow_upload is None
                            else allow_upload
                        ),
                        max_upload_bytes=settings.max_upload_bytes,
                        default_learner_id=settings.default_learner_id,
                        api_prefix=settings.api_prefix,
                    )
        elif title is not None or allow_upload is not None:
            settings = HostSettings(
                data_dir=settings.data_dir,
                title=title or settings.title,
                allow_upload=(
                    settings.allow_upload
                    if allow_upload is None
                    else allow_upload
                ),
                max_upload_bytes=settings.max_upload_bytes,
                default_learner_id=settings.default_learner_id,
                api_prefix=settings.api_prefix,
            )

        self.settings = settings
        self.settings.packages_dir.mkdir(parents=True, exist_ok=True)
        self.settings.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._router = build_router(settings)

    def mount(self, app: FastAPI) -> None:
        app.include_router(self._router)

    @property
    def router(self):
        return self._router
