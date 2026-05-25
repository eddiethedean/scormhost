from __future__ import annotations

import io
import zipfile

from fastapi.testclient import TestClient


def test_upload_rejects_parent_package_id(
    client: TestClient,
    minimal_scorm_zip: bytes,
) -> None:
    client.post(
        "/api/auth/register",
        json={
            "email": "inst2@example.com",
            "username": "inst2",
            "password": "password123",
            "display_name": "Instructor",
        },
    )
    response = client.post(
        "/api/packages?package_id=..",
        files={"file": ("demo.zip", minimal_scorm_zip, "application/zip")},
    )
    assert response.status_code == 400


def test_cmi_rejects_parent_package_id(client: TestClient) -> None:
    response = client.get("/api/scorm/../cmi")
    assert response.status_code == 404


def test_guest_cannot_read_user_cmi(
    client: TestClient,
    minimal_scorm_zip: bytes,
) -> None:
    client.post(
        "/api/auth/register",
        json={
            "email": "learner2@example.com",
            "username": "learner2",
            "password": "password123",
            "display_name": "Learner Two",
        },
    )
    upload = client.post(
        "/api/packages",
        files={"file": ("demo.zip", minimal_scorm_zip, "application/zip")},
    )
    package_id = upload.json()["id"]

    client.put(
        f"/api/scorm/{package_id}/cmi",
        params={"launch": "index.html"},
        json={"elements": {"cmi.core.lesson_status": "completed"}},
    )

    client.cookies.clear()
    client.cookies.set("scormhost_guest_id", "1")
    spoofed = client.get(
        f"/api/scorm/{package_id}/cmi",
        params={"launch": "index.html"},
    )
    assert spoofed.status_code == 200
    assert spoofed.json()["elements"].get("cmi.core.lesson_status") != "completed"


def test_zip_path_traversal_rejected(
    client: TestClient,
    minimal_scorm_zip: bytes,
) -> None:
    client.post(
        "/api/auth/register",
        json={
            "email": "zipinst@example.com",
            "username": "zipinst",
            "password": "password123",
            "display_name": "Zip Inst",
        },
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("../evil.txt", "bad")
    bad_zip = buffer.getvalue()
    response = client.post(
        "/api/packages",
        files={"file": ("bad.zip", bad_zip, "application/zip")},
    )
    assert response.status_code == 400
