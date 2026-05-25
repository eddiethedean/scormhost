from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HostSettings:
    """Runtime settings for the SCORM host."""

    data_dir: Path
    title: str = "SCORM Host"
    allow_upload: bool = True
    max_upload_bytes: int = 100 * 1024 * 1024
    default_learner_id: str = "demo-learner"
    api_prefix: str = ""

    @classmethod
    def from_env(cls, data_dir: Path | None = None) -> HostSettings:
        base = data_dir or Path(
            os.environ.get("SCORMHOST_DATA_DIR", "./data"),
        ).expanduser()
        return cls(
            data_dir=base.resolve(),
            title=os.environ.get("SCORMHOST_TITLE", "SCORM Host"),
            allow_upload=os.environ.get("SCORMHOST_ALLOW_UPLOAD", "true").lower()
            not in ("0", "false", "no"),
            max_upload_bytes=int(
                os.environ.get("SCORMHOST_MAX_UPLOAD_MB", "100"),
            )
            * 1024
            * 1024,
            default_learner_id=os.environ.get(
                "SCORMHOST_DEFAULT_LEARNER",
                "demo-learner",
            ),
            api_prefix=os.environ.get("SCORMHOST_API_PREFIX", "").rstrip("/"),
        )

    @property
    def packages_dir(self) -> Path:
        return self.data_dir / "packages"

    @property
    def sessions_dir(self) -> Path:
        return self.data_dir / "sessions"
