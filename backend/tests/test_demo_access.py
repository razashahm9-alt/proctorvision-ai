"""Tests for the optional private supervisor access gate."""

from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.main import app


def test_open_local_mode_requires_no_token(monkeypatch) -> None:
    monkeypatch.setattr(settings, "preload_model", False)
    with TestClient(app) as client:
        response = client.get("/api/auth/status")

    assert response.status_code == 200
    assert response.json() == {"required": False, "authenticated": True}


def test_private_mode_protects_archive_and_accepts_valid_token(
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "preload_model", False)
    monkeypatch.setattr(settings, "access_token", "temporary-supervisor-token")

    with TestClient(app) as client:
        status_response = client.get("/api/auth/status")
        blocked_response = client.get("/api/history/sessions")
        incorrect_response = client.post(
            "/api/auth/login",
            json={"access_token": "incorrect"},
        )
        login_response = client.post(
            "/api/auth/login",
            json={"access_token": "temporary-supervisor-token"},
        )
        archive_response = client.get("/api/history/sessions")
        logout_response = client.post("/api/auth/logout")
        blocked_again_response = client.get("/api/history/sessions")

    assert status_response.json() == {"required": True, "authenticated": False}
    assert blocked_response.status_code == 401
    assert incorrect_response.status_code == 401
    assert login_response.status_code == 200
    assert "HttpOnly" in login_response.headers["set-cookie"]
    assert archive_response.status_code == 200
    assert logout_response.status_code == 204
    assert blocked_again_response.status_code == 401
