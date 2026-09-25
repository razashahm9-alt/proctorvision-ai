"""Tests for stable temporal incident confirmation and clearing."""

from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.base import Base
from backend.app.database.repository import (
    get_monitoring_session,
    list_session_incidents,
)
from backend.app.detection.schemas import (
    BoundingBox,
    DetectionItem,
    FrameDetectionResponse,
)
from backend.app.services.incident_engine import IncidentEngine


@pytest.fixture
def database() -> Session:
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    testing_session = sessionmaker(bind=test_engine, expire_on_commit=False)
    with testing_session() as session:
        yield session
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def detection_result(*items: DetectionItem) -> FrameDetectionResponse:
    return FrameDetectionResponse(
        detected=bool(items),
        device_count=len(items),
        image_width=640,
        image_height=480,
        inference_ms=100.0,
        detections=list(items),
    )


def device(
    class_name: str,
    display_name: str,
    confidence: float,
    *,
    x1: int = 100,
) -> DetectionItem:
    return DetectionItem(
        class_name=class_name,
        display_name=display_name,
        confidence=confidence,
        box=BoundingBox(x1=x1, y1=100, x2=x1 + 120, y2=300),
    )


def test_phone_requires_three_of_five_frames_and_saves_evidence(
    database: Session, tmp_path: Path
) -> None:
    started = datetime(2026, 9, 25, 14, 0, 0)
    engine = IncidentEngine(database, evidence_directory=tmp_path)
    monitoring = engine.start(started_at=started)
    phone = device("cell phone", "Mobile Phone", 0.81)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    first = engine.process_frame(
        detection_result(phone), frame=frame, observed_at=started
    )
    second = engine.process_frame(
        detection_result(phone),
        frame=frame,
        observed_at=started + timedelta(milliseconds=200),
    )
    third = engine.process_frame(
        detection_result(phone),
        frame=frame,
        observed_at=started + timedelta(milliseconds=400),
    )

    assert first.should_block_preview is False
    assert second.play_alert_sound is False
    assert third.should_block_preview is True
    assert third.play_alert_sound is True
    assert third.active_incidents[0].alert_message == "Mobile Phone Detected"
    assert len(third.events) == 1
    assert third.events[0].event_type == "started"
    assert Path(third.events[0].evidence_path).is_file()

    incidents = list_session_incidents(database, monitoring.id)
    assert len(incidents) == 1
    assert incidents[0].device_key == "cell phone"
    assert incidents[0].status == "Active"


def test_active_incident_tracks_peak_and_resolves_after_delay(
    database: Session, tmp_path: Path
) -> None:
    started = datetime(2026, 9, 25, 14, 10, 0)
    engine = IncidentEngine(database, evidence_directory=tmp_path)
    monitoring = engine.start(started_at=started)
    phone = device("cell phone", "Mobile Phone", 0.60)

    for offset in (0.0, 0.2, 0.4):
        engine.process_frame(
            detection_result(phone),
            observed_at=started + timedelta(seconds=offset),
        )

    two_phones = detection_result(
        device("cell phone", "Mobile Phone", 0.92),
        device("cell phone", "Mobile Phone", 0.75, x1=300),
    )
    engine.process_frame(
        two_phones,
        observed_at=started + timedelta(seconds=1),
    )
    waiting = engine.process_frame(
        detection_result(),
        observed_at=started + timedelta(seconds=2),
    )
    resolved = engine.process_frame(
        detection_result(),
        observed_at=started + timedelta(seconds=4.1),
    )

    assert waiting.should_block_preview is True
    assert resolved.should_block_preview is False
    assert resolved.events[0].event_type == "resolved"
    incident = list_session_incidents(database, monitoring.id)[0]
    assert incident.status == "Resolved"
    assert incident.maximum_confidence == pytest.approx(0.92)
    assert incident.maximum_count == 2


def test_two_device_types_create_separate_incidents(
    database: Session, tmp_path: Path
) -> None:
    started = datetime(2026, 9, 25, 14, 20, 0)
    engine = IncidentEngine(database, evidence_directory=tmp_path)
    monitoring = engine.start(started_at=started)
    result = detection_result(
        device("cell phone", "Mobile Phone", 0.85),
        device("laptop", "Laptop / Computer", 0.76, x1=300),
    )

    for offset in (0.0, 0.2):
        state = engine.process_frame(
            result,
            observed_at=started + timedelta(seconds=offset),
        )
        assert state.play_alert_sound is False
    confirmed = engine.process_frame(
        result,
        observed_at=started + timedelta(seconds=0.4),
    )

    assert confirmed.play_alert_sound is True
    assert len(confirmed.active_incident_ids) == 2
    assert {event.device_key for event in confirmed.events} == {
        "cell phone",
        "laptop",
    }
    assert get_monitoring_session(database, monitoring.id).total_incidents == 2


def test_finish_stops_active_engine_incident(
    database: Session, tmp_path: Path
) -> None:
    started = datetime(2026, 9, 25, 14, 30, 0)
    engine = IncidentEngine(database, evidence_directory=tmp_path)
    monitoring = engine.start(started_at=started)
    tv = device("tv", "TV / LCD / Monitor", 0.72)
    for offset in (0.0, 0.2, 0.4):
        engine.process_frame(
            detection_result(tv),
            observed_at=started + timedelta(seconds=offset),
        )

    finished = engine.finish(ended_at=started + timedelta(seconds=3))
    incident = list_session_incidents(database, monitoring.id)[0]

    assert finished.status == "Completed"
    assert incident.status == "Stopped"
    assert engine.started is False
