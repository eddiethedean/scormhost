from __future__ import annotations

from urllib.parse import quote


def safe_next_path(raw: str | None, *, default: str = "/") -> str:
    """Allow only same-origin relative paths for post-login redirects."""
    if not raw:
        return default
    path = raw.strip()
    if not path.startswith("/") or path.startswith("//"):
        return default
    return path


def login_url(next_path: str | None = None, *, default_next: str = "/") -> str:
    target = safe_next_path(next_path, default=default_next)
    if target == default_next:
        return "/login"
    return f"/login?next={quote(target, safe='/?:=&')}"
