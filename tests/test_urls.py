from scormhost.auth.urls import login_url, safe_next_path


def test_safe_next_path_rejects_external() -> None:
    assert safe_next_path("https://evil.example/phish") == "/"
    assert safe_next_path("//evil.example/path") == "/"
    assert safe_next_path(None) == "/"


def test_safe_next_path_allows_local() -> None:
    assert safe_next_path("/launch/abc") == "/launch/abc"
    assert (
        safe_next_path("/launch/abc?launch=index.html")
        == "/launch/abc?launch=index.html"
    )


def test_login_url_includes_next() -> None:
    assert login_url("/launch/pkg-1") == "/login?next=/launch/pkg-1"
    assert login_url("/") == "/login"
