from pathlib import Path

from fastapi.testclient import TestClient

from scormhost import create_scorm_app


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_upload_launch_and_cmi(
    client: TestClient,
    minimal_scorm_zip: bytes,
) -> None:
    client.post(
        "/api/auth/register",
        json={
            "email": "uploader@example.com",
            "username": "uploader",
            "password": "password123",
            "display_name": "Uploader",
        },
    )
    response = client.post(
        "/api/packages",
        files={
            "file": ("minimal-demo.zip", minimal_scorm_zip, "application/zip"),
        },
    )
    assert response.status_code == 201
    package_id = response.json()["id"]

    launch = client.get(f"/launch/{package_id}")
    assert launch.status_code == 200
    assert "scorm12-api.js" in launch.text
    assert "scormhost-content" in launch.text

    content = client.get(f"/content/{package_id}/index.html")
    assert content.status_code == 200
    assert "text/html" in content.headers.get("content-type", "")

    cmi_put = client.put(
        f"/api/scorm/{package_id}/cmi",
        params={"launch": "index.html"},
        json={"elements": {"cmi.core.lesson_status": "incomplete"}},
    )
    assert cmi_put.status_code == 200

    cmi_get = client.get(
        f"/api/scorm/{package_id}/cmi",
        params={"launch": "index.html"},
    )
    assert cmi_get.json()["elements"]["cmi.core.lesson_status"] == "incomplete"


def test_api_prefix_in_launch_page(
    tmp_path: Path,
    minimal_scorm_zip: bytes,
) -> None:
    db_path = tmp_path / "prefix.db"
    application = create_scorm_app(
        data_dir=tmp_path / "data_prefix",
        secret_key="test-secret-key-for-jwt-signing-only",
        database_url=f"sqlite:///{db_path}",
        api_prefix="/scorm",
    )
    with TestClient(application) as prefixed:
        prefixed.post(
            "/api/auth/register",
            json={
                "email": "pfx@example.com",
                "username": "pfxuser",
                "password": "password123",
                "display_name": "Prefix",
            },
        )
        upload = prefixed.post(
            "/api/packages",
            files={"file": ("demo.zip", minimal_scorm_zip, "application/zip")},
        )
        assert upload.status_code == 201
        package_id = upload.json()["id"]
        launch = prefixed.get(f"/launch/{package_id}")
        assert launch.status_code == 200
        assert "/scorm/api/scorm/" in launch.text
        assert "/scorm/static/scorm12-api.js" in launch.text
