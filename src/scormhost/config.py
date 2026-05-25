from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() not in ("0", "false", "no")


@dataclass(frozen=True)
class HostSettings:
    """Runtime settings for the SCORM host."""

    data_dir: Path
    title: str = "SCORM Host"
    allow_upload: bool = True
    max_upload_bytes: int = 100 * 1024 * 1024
    default_learner_id: str = "demo-learner"
    api_prefix: str = ""
    database_url: str = ""
    secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    allow_registration: bool = True
    require_auth: bool = False
    cookie_secure: bool = False
    auto_migrate: bool = True
    bootstrap_admin_email: str | None = None

    @classmethod
    def from_env(cls, data_dir: Path | None = None) -> HostSettings:
        base = (
            data_dir
            or Path(
                os.environ.get("SCORMHOST_DATA_DIR", "./data"),
            ).expanduser()
        )
        resolved = base.resolve()
        db_default = f"sqlite:///{resolved / 'scormhost.db'}"
        secret = os.environ.get("SCORMHOST_SECRET_KEY") or secrets.token_urlsafe(32)
        return cls(
            data_dir=resolved,
            title=os.environ.get("SCORMHOST_TITLE", "SCORM Host"),
            allow_upload=_env_bool("SCORMHOST_ALLOW_UPLOAD", True),
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
            database_url=os.environ.get("SCORMHOST_DATABASE_URL", db_default),
            secret_key=secret,
            jwt_algorithm=os.environ.get("SCORMHOST_JWT_ALGORITHM", "HS256"),
            access_token_expire_minutes=int(
                os.environ.get("SCORMHOST_ACCESS_TOKEN_MINUTES", "30"),
            ),
            refresh_token_expire_days=int(
                os.environ.get("SCORMHOST_REFRESH_TOKEN_DAYS", "7"),
            ),
            allow_registration=_env_bool("SCORMHOST_ALLOW_REGISTRATION", True),
            require_auth=_env_bool("SCORMHOST_REQUIRE_AUTH", False),
            cookie_secure=_env_bool("SCORMHOST_COOKIE_SECURE", False),
            auto_migrate=_env_bool("SCORMHOST_AUTO_MIGRATE", True),
            bootstrap_admin_email=os.environ.get("SCORMHOST_BOOTSTRAP_ADMIN_EMAIL"),
        )

    @property
    def packages_dir(self) -> Path:
        return self.data_dir / "packages"

    @property
    def sessions_dir(self) -> Path:
        return self.data_dir / "sessions"

    @property
    def access_cookie_name(self) -> str:
        return "scormhost_access_token"

    @property
    def refresh_cookie_name(self) -> str:
        return "scormhost_refresh_token"

    @property
    def guest_cookie_name(self) -> str:
        return "scormhost_guest_id"
