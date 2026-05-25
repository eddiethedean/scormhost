import pytest
from fastapi.testclient import TestClient

from scormhost import create_scorm_app


@pytest.fixture
def client(tmp_path) -> TestClient:
    app = create_scorm_app(data_dir=tmp_path / "data", title="Test Host")
    return TestClient(app)


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_upload_launch_and_cmi(
    client: TestClient,
    minimal_scorm_zip: bytes,
) -> None:
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
        params={"learner_id": "alice", "launch": "index.html"},
        json={"elements": {"cmi.core.lesson_status": "incomplete"}},
    )
    assert cmi_put.status_code == 200

    cmi_get = client.get(
        f"/api/scorm/{package_id}/cmi",
        params={"learner_id": "alice", "launch": "index.html"},
    )
    assert cmi_get.json()["elements"]["cmi.core.lesson_status"] == "incomplete"
