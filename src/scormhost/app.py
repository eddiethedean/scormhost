from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from scormhost.config import HostSettings
from scormhost.host import ScormHost


def create_scorm_app(
    *,
    data_dir: str | Path = "./data",
    title: str = "SCORM Host",
    allow_upload: bool = True,
    default_learner_id: str = "demo-learner",
) -> FastAPI:
    """
    Create a FastAPI app that hosts SCORM 1.2 / 2004 ZIP packages.

    Deploy to FastAPI Cloud with::

        fastapi deploy

    Set ``SCORMHOST_DATA_DIR`` for persistent package storage on the platform.
    """
    settings = HostSettings(
        data_dir=Path(data_dir).expanduser().resolve(),
        title=title,
        allow_upload=allow_upload,
        default_learner_id=default_learner_id,
    )
    settings.packages_dir.mkdir(parents=True, exist_ok=True)
    settings.sessions_dir.mkdir(parents=True, exist_ok=True)

    app = FastAPI(
        title=title,
        description="SCORM package host powered by scormhost",
        version="0.1.0",
    )
    ScormHost(settings).mount(app)
    return app
