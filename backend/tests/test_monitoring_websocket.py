"""Integration tests for real-time WebSocket monitoring transport."""

import json
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.api import monitoring as monitoring_api
from backend.app.database.base import Base
from backend.app.database.repository import (
    get_monitoring_session,
    list_monitoring_sessions,
    list_session_incidents,
)
from backend.app.detection.schemas import (
    BoundingBox,
    DetectionItem,
    FrameDetectionResponse,
)
from backend.app.services.incident_engine import IncidentEngine


class FakeDetector:
    """Return a deterministic result without loading YOLO weights."""

    def __init__(self, result: FrameDetectionResponse) -> None:
        self.result = result

    def detect(self, _frame: np.ndarray) -> FrameDetectionResponse:
        return self.result


@pytest.fixture
def database_factory():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    factory = sessionmaker(bind=test_engine, expire_on_commit=False)
    yield factory
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def phone_result() -> FrameDetectionResponse:
    phone = DetectionItem(
        class_name="cell phone",
        display_name="Mobile Phone",
        confidence=0.88,
        box=BoundingBox(x1=100, y1=80, x2=260, y2=350),
    )
    return FrameDetectionResponse(
        detected=True,
        device_count=1,
        image_width=640,
        image_height=480,
        inference_ms=95.0,
        detections=[phone],
    )


def jpeg_frame() -> bytes:
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    success, encoded = cv2.imencode(".jpg", frame)
    assert success
    return encoded.tobytes()


def create_test_client(
    monkeypatch: pytest.MonkeyPatch,
    database_factory,
    evidence_directory: Path,
    detector_result: FrameDetectionResponse,
) -> TestClient:
    monkeypatch.setattr(
        monitoring_api,
        "create_database_session",
        database_factory,
    )
    monkeypatch.setattr(
        monitoring_api,
        "create_incident_engine",
        lambda database: IncidentEngine(
            database,
            evidence_directory=evidence_directory,
        ),
    )
    monkeypatch.setattr(
        monitoring_api,
        "get_detector",
        lambda: FakeDetector(detector_result),
    )
    application = FastAPI()
    application.include_router(monitoring_api.router, prefix="/api")
    return TestClient(application)


def test_websocket_confirms_phone_and_finishes_session(
    monkeypatch: pytest.MonkeyPatch,
    database_factory,
    tmp_path: Path,
) -> None:
    client = create_test_client(
        monkeypatch,
        database_factory,
        tmp_path,
        phone_result(),
    )

    with client.websocket_connect("/api/ws/monitoring") as websocket:
        started = websocket.receive_json()
        assert started["type"] == "session_started"

        responses = []
        for _ in range(3):
            websocket.send_bytes(jpeg_frame())
            responses.append(websocket.receive_json())

        assert responses[0]["type"] == "frame_result"
        assert responses[0]["monitoring"]["should_block_preview"] is False
        assert responses[2]["monitoring"]["should_block_preview"] is True
        assert responses[2]["monitoring"]["play_alert_sound"] is True
        assert (
            responses[2]["monitoring"]["active_incidents"][0]["alert_message"]
            == "Mobile Phone Detected"
        )

        websocket.send_text(json.dumps({"type": "stop"}))
        finished = websocket.receive_json()
        assert finished["type"] == "session_finished"
        assert finished["total_incidents"] == 1

    with database_factory() as database:
        monitoring_session = get_monitoring_session(database, started["session_id"])
        assert monitoring_session is not None
        assert monitoring_session.status == "Completed"
        incidents = list_session_incidents(database, monitoring_session.id)
        assert len(incidents) == 1
        assert incidents[0].status == "Stopped"
        assert Path(incidents[0].evidence_path).is_file()


def test_invalid_frame_is_recoverable_and_ping_still_works(
    monkeypatch: pytest.MonkeyPatch,
    database_factory,
    tmp_path: Path,
) -> None:
    client = create_test_client(
        monkeypatch,
        database_factory,
        tmp_path,
        phone_result(),
    )

    with client.websocket_connect("/api/ws/monitoring") as websocket:
        websocket.receive_json()
        websocket.send_bytes(b"not-an-image")
        error = websocket.receive_json()
        assert error == {
            "type": "error",
            "code": "invalid_frame",
            "message": "The binary payload is not a valid image frame.",
            "recoverable": True,
        }

        websocket.send_text(json.dumps({"type": "ping"}))
        assert websocket.receive_json() == {"type": "pong"}
        websocket.send_text(json.dumps({"type": "stop"}))
        assert websocket.receive_json()["type"] == "session_finished"


def test_disconnect_automatically_finishes_session(
    monkeypatch: pytest.MonkeyPatch,
    database_factory,
    tmp_path: Path,
) -> None:
    client = create_test_client(
        monkeypatch,
        database_factory,
        tmp_path,
        phone_result(),
    )

    with client.websocket_connect("/api/ws/monitoring") as websocket:
        session_id = websocket.receive_json()["session_id"]

    with database_factory() as database:
        sessions = list_monitoring_sessions(database)
        assert len(sessions) == 1
        assert sessions[0].id == session_id
        assert sessions[0].status == "Completed"
