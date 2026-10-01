from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_root() -> None:
    response = client.get("/api")

    assert response.status_code == 200
    assert response.json()["application"] == "ProctorVision AI API"


def test_health_check() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert {
        key: payload[key]
        for key in ("status", "application", "version", "detector", "model")
    } == {
        "status": "healthy",
        "application": "ProctorVision AI",
        "version": "0.8.1",
        "detector": "not_loaded",
        "model": "yolo11s",
    }
    assert payload["runtime"] in {"OpenVINO CPU", "PyTorch CPU"}
    assert payload["access_protected"] is False
    assert payload["frontend"] in {"available", "not_built"}


def test_readiness_reports_unloaded_detector() -> None:
    response = client.get("/api/ready")

    assert response.status_code == 503
    assert response.json() == {
        "ready": False,
        "database": "ready",
        "detector": "not_loaded",
        "runtime": response.json()["runtime"],
    }
