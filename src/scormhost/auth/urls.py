from __future__ import annotations

from collections.abc import Callable
from urllib.parse import quote


def safe_next_path(raw: str | None, *, default: str = "/") -> str:
    """Allow only same-origin relative paths for post-login redirects."""
    if not raw:
        return default
    path = raw.strip()
    if not path.startswith("/") or path.startswith("//"):
        return default
    return path


def login_url(
    next_path: str | None = None,
    *,
    default_next: str = "/",
    url: Callable[[str], str] | None = None,
) -> str:
    def path(p: str) -> str:
        if url is None:
            return p
        return url(p)

    target = safe_next_path(next_path, default=default_next)
    login_path = path("/login")
    if target == default_next:
        return login_path
    return f"{login_path}?next={quote(target, safe='/?:=&')}"
