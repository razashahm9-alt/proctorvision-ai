"""Integration tests for session review, evidence, and CSV export."""

from __future__ import annotations

import csv
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.api import history as history_api
from backend.app.database.base import Base, get_db
from backend.app.database.repository import (
    finish_monitoring_session,
    resolve_incident,
    start_incident,
    start_monitoring_session,
)


@pytest.fixture
def history_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    factory = sessionmaker(bind=test_engine, expire_on_commit=False)
    evidence_root = tmp_path / "evidence"
    monkeypatch.setattr(history_api.settings, "evidence_directory", evidence_root)

    def override_database():
        with factory() as database:
            yield database

    application = FastAPI()
    application.include_router(history_api.router, prefix="/api")
    application.dependency_overrides[get_db] = override_database

    with factory() as database:
        started = datetime(2026, 9, 30, 7, 0, 0)
        monitoring_session = start_monitoring_session(
            database,
            started_at=started,
            session_id="SESSION-TEST-001",
        )
        evidence_directory = evidence_root / monitoring_session.id
        evidence_directory.mkdir(parents=True)
        evidence_path = evidence_directory / "EVT-PHONE.jpg"
        evidence_path.write_bytes(b"test-jpeg-content")
        phone = start_incident(
            database,
            session_id=monitoring_session.id,
            incident_id="EVT-PHONE",
            device_key="cell phone",
            device_name="Mobile Phone",
            confidence=0.86,
            count=1,
            evidence_path=str(evidence_path),
            detected_at=started + timedelta(seconds=2),
        )
        resolve_incident(
            database,
            phone.id,
            cleared_at=started + timedelta(seconds=7),
        )
        start_incident(
            database,
            session_id=monitoring_session.id,
            incident_id="EVT-TV",
            device_key="tv",
            device_name="TV / LCD / Monitor",
            confidence=0.72,
            count=1,
            detected_at=started + timedelta(seconds=9),
        )
        finish_monitoring_session(
            database,
            monitoring_session.id,
            ended_at=started + timedelta(seconds=12),
        )

    with TestClient(application) as client:
        yield client

    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def test_lists_and_loads_complete_session(history_client: TestClient) -> None:
    response = history_client.get("/api/history/sessions")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == "SESSION-TEST-001"
    assert payload["items"][0]["total_incidents"] == 2
    assert payload["items"][0]["duration_seconds"] == 12.0
    assert payload["items"][0]["started_at"].endswith("Z")

    detail = history_client.get("/api/history/sessions/SESSION-TEST-001")
    assert detail.status_code == 200
    incidents = detail.json()["incidents"]
    assert [incident["id"] for incident in incidents] == ["EVT-PHONE", "EVT-TV"]
    assert incidents[0]["evidence_available"] is True
    assert incidents[0]["duration_seconds"] == 5.0
    assert incidents[1]["status"] == "Stopped"
    assert incidents[1]["evidence_available"] is False


def test_serves_evidence_and_handles_missing_image(history_client: TestClient) -> None:
    evidence = history_client.get("/api/history/incidents/EVT-PHONE/evidence")
    assert evidence.status_code == 200
    assert evidence.headers["content-type"] == "image/jpeg"
    assert evidence.content == b"test-jpeg-content"

    missing = history_client.get("/api/history/incidents/EVT-TV/evidence")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Evidence image not found."


def test_exports_excel_friendly_csv(history_client: TestClient) -> None:
    response = history_client.get(
        "/api/history/sessions/SESSION-TEST-001/export.csv"
    )
    assert response.status_code == 200
    assert "SESSION-TEST-001.csv" in response.headers["content-disposition"]
    assert response.content.startswith(b"\xef\xbb\xbf")

    rows = list(csv.DictReader(StringIO(response.content.decode("utf-8-sig"))))
    assert len(rows) == 2
    assert rows[0]["Device"] == "Mobile Phone"
    assert rows[0]["Maximum Confidence (%)"] == "86.00"
    assert rows[0]["Evidence File"] == "EVT-PHONE.jpg"
    assert rows[1]["Device"] == "TV / LCD / Monitor"
    assert rows[1]["Status"] == "Stopped"


def test_unknown_session_returns_404(history_client: TestClient) -> None:
    response = history_client.get("/api/history/sessions/SESSION-UNKNOWN")
    assert response.status_code == 404
    assert response.json()["detail"] == "Monitoring session not found."
