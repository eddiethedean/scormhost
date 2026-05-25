from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "minimal-scorm12"


@pytest.fixture
def minimal_scorm_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in FIXTURE_DIR.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(FIXTURE_DIR).as_posix())
    return buffer.getvalue()
