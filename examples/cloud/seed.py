"""Load bundled LXPack sample courses on first startup."""

from __future__ import annotations

import os
from pathlib import Path

from scormhost.config import HostSettings
from scormhost.packages import extract_scorm_zip
from scormhost.storage import PackageStore

_BUNDLED_DIR = Path(__file__).resolve().parent / "bundled"

# scormhost only hosts SCORM 1.2 / 2004, so we only seed SCORM targets here.
_BUNDLED_PACKAGES: dict[str, str] = {
    "security-awareness": "security-awareness-scorm12.zip",
    "branching-demo": "branching-demo-scorm2004.zip",
    "xapi-awareness": "xapi-awareness-scorm12.zip",
}


def seed_bundled_course(settings: HostSettings) -> str | None:
    """
    Ingest bundled SCORM ZIPs if they are not already present.

    Set ``SCORMHOST_SEED_BUNDLED_COURSE=0`` to disable (e.g. empty production disk).
    Returns one seeded package id (if any), else None.
    """
    if os.environ.get("SCORMHOST_SEED_BUNDLED_COURSE", "true").lower() in (
        "0",
        "false",
        "no",
    ):
        return None

    store = PackageStore(settings)
    seeded: str | None = None
    for package_id, filename in _BUNDLED_PACKAGES.items():
        zip_path = _BUNDLED_DIR / filename
        if not zip_path.is_file():
            continue
        try:
            if store.meta_path(package_id).is_file():
                continue
        except ValueError:
            continue

        zip_bytes = zip_path.read_bytes()
        extract_scorm_zip(
            store,
            zip_bytes,
            zip_path.name,
            preferred_id=package_id,
        )
        seeded = seeded or package_id

    return seeded
