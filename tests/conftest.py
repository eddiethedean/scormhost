from __future__ import annotations

import io
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scormhost import create_scorm_app

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "minimal-scorm12"


@pytest.fixture
def minimal_scorm_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in FIXTURE_DIR.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(FIXTURE_DIR).as_posix())
    return buffer.getvalue()


@pytest.fixture
def app(tmp_path: Path):
    db_path = tmp_path / "test.db"
    return create_scorm_app(
        data_dir=tmp_path / "data",
        title="Test Host",
        require_auth=False,
        secret_key="test-secret-key-for-jwt-signing-only",
        database_url=f"sqlite:///{db_path}",
        auto_migrate=True,
    )


@pytest.fixture
def client(app) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_client(tmp_path: Path) -> Iterator[TestClient]:
    """App with SCORMHOST_REQUIRE_AUTH=true (login required to take courses)."""
    db_path = tmp_path / "auth_strict.db"
    application = create_scorm_app(
        data_dir=tmp_path / "data_strict",
        title="Auth Test",
        require_auth=True,
        secret_key="test-secret-key-for-jwt-signing-only",
        database_url=f"sqlite:///{db_path}",
        auto_migrate=True,
    )
    with TestClient(application) as test_client:
        yield test_client
