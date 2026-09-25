from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_root() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["application"] == "ProctorVision AI API"


def test_health_check() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "application": "ProctorVision AI",
        "version": "0.3.0",
        "detector": "not_loaded",
    }
