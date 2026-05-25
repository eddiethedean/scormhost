from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path

from scormhost.storage import PackageStore


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

        with zipfile.ZipFile(zip_path) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = info.filename.replace("\\", "/")
                if name.startswith("/") or ".." in name.split("/"):
                    raise ValueError(f"Unsafe path in zip: {info.filename}")
            zf.extractall(tmp_path / "package")

        extract_dir = tmp_path / "package"
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
    sessions = store.settings.sessions_dir / package_id
    if sessions.is_dir():
        shutil.rmtree(sessions)
