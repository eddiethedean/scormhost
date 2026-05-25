"""Load the bundled LXPack sample course on first startup."""

from __future__ import annotations

import os
from pathlib import Path

from scormhost.config import HostSettings
from scormhost.packages import extract_scorm_zip
from scormhost.storage import PackageStore

BUNDLED_PACKAGE_ID = "security-awareness"
_BUNDLED_DIR = Path(__file__).resolve().parent / "bundled"
BUNDLED_ZIP = _BUNDLED_DIR / "security-awareness-scorm12.zip"


def seed_bundled_course(settings: HostSettings) -> str | None:
    """
    Ingest the bundled SCORM 1.2 ZIP if that package is not already present.

    Set ``SCORMHOST_SEED_BUNDLED_COURSE=0`` to disable (e.g. empty production disk).
    Returns the package id when seeded, else None.
    """
    if os.environ.get("SCORMHOST_SEED_BUNDLED_COURSE", "true").lower() in (
        "0",
        "false",
        "no",
    ):
        return None

    if not BUNDLED_ZIP.is_file():
        return None

    store = PackageStore(settings)
    try:
        if store.meta_path(BUNDLED_PACKAGE_ID).is_file():
            return None
    except ValueError:
        pass

    zip_bytes = BUNDLED_ZIP.read_bytes()
    package_id = extract_scorm_zip(
        store,
        zip_bytes,
        BUNDLED_ZIP.name,
        preferred_id=BUNDLED_PACKAGE_ID,
    )
    return package_id
