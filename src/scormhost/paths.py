from __future__ import annotations

import re
from pathlib import Path

_PACKAGE_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
_RESERVED_PACKAGE_IDS = frozenset({".", ".."})


class PathTraversalError(ValueError):
    pass


class InvalidPackageIdError(ValueError):
    pass


def validate_package_id(package_id: str) -> str:
    """Reject path segments and reserved names; return the id unchanged."""
    if not package_id or package_id in _RESERVED_PACKAGE_IDS:
        raise InvalidPackageIdError("Invalid package id")
    if not _PACKAGE_ID_RE.match(package_id):
        raise InvalidPackageIdError("Invalid package id")
    return package_id


def package_root_under(packages_dir: Path, package_id: str) -> Path:
    """Resolved package directory guaranteed under packages_dir."""
    pid = validate_package_id(package_id)
    return resolve_under_root(packages_dir.resolve(), pid)


def session_dir_under(sessions_dir: Path, package_id: str) -> Path:
    """Resolved session directory for a package under sessions_dir."""
    pid = validate_package_id(package_id)
    return resolve_under_root(sessions_dir.resolve(), pid)


def is_safe_launch_href(href: str) -> bool:
    """Relative launch paths only (no schemes or protocol-relative URLs)."""
    if not href or not href.strip():
        return False
    normalized = href.strip().replace("\\", "/")
    if normalized.startswith("/") or normalized.startswith("//"):
        return False
    if "://" in normalized:
        return False
    lower = normalized.lower()
    if lower.startswith("javascript:") or lower.startswith("data:"):
        return False
    if ".." in normalized.split("/"):
        return False
    return True


def resolve_under_root(root: Path, *parts: str) -> Path:
    """Resolve a path and ensure it stays inside root (symlink-safe)."""
    root = root.resolve()
    candidate = root.joinpath(*parts).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise PathTraversalError(f"Path escapes package root: {candidate}") from exc
    return candidate


def safe_content_path(package_root: Path, rel_path: str) -> Path:
    rel = rel_path.lstrip("/").replace("\\", "/")
    if not rel or rel.endswith("/"):
        raise PathTraversalError("Invalid content path")
    segments = rel.split("/")
    if ".." in segments:
        raise PathTraversalError("Path traversal not allowed")
    return resolve_under_root(package_root, *segments)
