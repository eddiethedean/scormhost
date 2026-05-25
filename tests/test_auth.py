from fastapi.testclient import TestClient


def test_register_first_user_is_admin(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/auth/register",
        json={
            "email": "admin@example.com",
            "username": "admin",
            "password": "password123",
            "display_name": "Admin User",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["role"] == "admin"
    assert data["access_token"]
    assert auth_client.cookies.get("scormhost_access_token")


def test_login_and_me(auth_client: TestClient) -> None:
    auth_client.post(
        "/api/auth/register",
        json={
            "email": "learner@example.com",
            "username": "learner1",
            "password": "password123",
            "display_name": "Learner",
        },
    )
    auth_client.cookies.clear()

    login = auth_client.post(
        "/api/auth/login",
        json={"email": "learner@example.com", "password": "password123"},
    )
    assert login.status_code == 200

    me = auth_client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "learner@example.com"


def test_catalog_is_public_by_default(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 200
    assert "Launch" in response.text or "courses" in response.text.lower()


def test_launch_without_login(client: TestClient, minimal_scorm_zip: bytes) -> None:
    client.post(
        "/api/auth/register",
        json={
            "email": "inst@example.com",
            "username": "instructor",
            "password": "password123",
            "display_name": "Instructor",
        },
    )
    uploaded = client.post(
        "/api/packages",
        files={"file": ("demo.zip", minimal_scorm_zip, "application/zip")},
    )
    assert uploaded.status_code == 201
    package_id = uploaded.json()["id"]

    client.cookies.clear()
    launch = client.get(f"/launch/{package_id}")
    assert launch.status_code == 200


def test_upload_requires_login(client: TestClient, minimal_scorm_zip: bytes) -> None:
    response = client.post(
        "/api/packages",
        files={"file": ("demo.zip", minimal_scorm_zip, "application/zip")},
    )
    assert response.status_code == 401


def test_catalog_redirects_when_strict_auth(auth_client: TestClient) -> None:
    response = auth_client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"].startswith("/login")


def test_login_page_preserves_next(client: TestClient) -> None:
    page = client.get("/login?next=/launch/demo-id")
    assert page.status_code == 200
    assert "/launch/demo-id" in page.text


def test_login_password_max_length(auth_client: TestClient) -> None:
    auth_client.post(
        "/api/auth/register",
        json={
            "email": "longpw@example.com",
            "username": "longpwuser",
            "password": "password123",
            "display_name": "Long PW",
        },
    )
    auth_client.cookies.clear()
    response = auth_client.post(
        "/api/auth/login",
        json={"email": "longpw@example.com", "password": "x" * 200},
    )
    assert response.status_code == 422


def test_password_change_revokes_refresh(auth_client: TestClient) -> None:
    auth_client.post(
        "/api/auth/register",
        json={
            "email": "revoke@example.com",
            "username": "revokeuser",
            "password": "password123",
            "display_name": "Revoke Test",
        },
    )
    refresh_cookie = auth_client.cookies.get("scormhost_refresh_token")
    assert refresh_cookie

    auth_client.patch(
        "/api/auth/me/password",
        json={
            "current_password": "password123",
            "new_password": "newpassword123",
        },
    )
    auth_client.cookies.set("scormhost_refresh_token", refresh_cookie)
    refresh = auth_client.post("/api/auth/refresh")
    assert refresh.status_code == 401


def test_strict_auth_redirect_includes_next(auth_client: TestClient) -> None:
    response = auth_client.get("/launch/missing", follow_redirects=False)
    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith("/login?next=")
    assert "launch" in location
