def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_json()["database"] == "ok"


def test_homepage_responds(client):
    response = client.get("/")
    assert response.status_code in (200, 302)


def test_security_headers(client):
    response = client.get("/")
    assert "Content-Security-Policy" in response.headers
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Request-ID")


def test_legacy_admin_path_hidden(client):
    response = client.get("/admin/login")
    assert response.status_code == 404
