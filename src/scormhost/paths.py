from __future__ import annotations

from pathlib import Path


class PathTraversalError(ValueError):
    pass


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
