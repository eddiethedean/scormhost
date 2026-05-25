from __future__ import annotations

import shutil
import stat
import tempfile
import zipfile
from pathlib import Path

from scormhost.paths import session_dir_under
from scormhost.storage import PackageStore

_MAX_UNCOMPRESSED_RATIO = 3


def _verify_extracted_tree(extract_root: Path, max_bytes: int) -> None:
    extract_root = extract_root.resolve()
    total = 0
    for path in extract_root.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"Symlinks not allowed in package: {path.name}")
        if not path.is_file():
            continue
        if not path.is_symlink():
            resolved = path.resolve()
            try:
                resolved.relative_to(extract_root)
            except ValueError as exc:
                raise ValueError(f"Unsafe path in zip: {path}") from exc
        size = path.stat().st_size
        total += size
        if total > max_bytes:
            raise ValueError("Package uncompressed size exceeds limit")
    if total == 0:
        raise ValueError("Zip contains no files")


def extract_scorm_zip(
    store: PackageStore,
    zip_bytes: bytes,
    filename: str,
    preferred_id: str | None = None,
    uploaded_by_id: int | None = None,
) -> str:
    if not zip_bytes:
        raise ValueError("Empty upload")

    with tempfile.TemporaryDirectory(prefix="scormhost-") as tmp:
        tmp_path = Path(tmp)
        zip_path = tmp_path / "upload.zip"
        zip_path.write_bytes(zip_bytes)

        max_uncompressed = store.settings.max_upload_bytes * _MAX_UNCOMPRESSED_RATIO
        with zipfile.ZipFile(zip_path) as zf:
            uncompressed_total = 0
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = info.filename.replace("\\", "/")
                if name.startswith("/") or ".." in name.split("/"):
                    raise ValueError(f"Unsafe path in zip: {info.filename}")
                mode = (info.external_attr >> 16) & 0o170000
                if mode == stat.S_IFLNK:
                    raise ValueError(f"Symlinks not allowed in zip: {info.filename}")
                uncompressed_total += info.file_size
                if uncompressed_total > max_uncompressed:
                    raise ValueError("Package uncompressed size exceeds limit")
            zf.extractall(tmp_path / "package")

        extract_dir = tmp_path / "package"
        _verify_extracted_tree(extract_dir, max_uncompressed)
        return store.ingest_extracted(
            extract_dir,
            filename,
            preferred_id,
            uploaded_by_id=uploaded_by_id,
        )


def can_delete_package(meta: dict, actor_user_id: int | None, is_admin: bool) -> bool:
    if is_admin:
        return True
    owner = meta.get("uploaded_by_id")
    if owner is None or actor_user_id is None:
        return is_admin
    return int(owner) == actor_user_id


def delete_package(store: PackageStore, package_id: str) -> None:
    root = store.package_root(package_id)
    if root.is_dir():
        shutil.rmtree(root)
    try:
        sessions = session_dir_under(store.settings.sessions_dir, package_id)
    except ValueError:
        return
    if sessions.is_dir():
        shutil.rmtree(sessions)
