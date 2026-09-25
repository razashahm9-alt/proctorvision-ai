"""Tests for persistent monitoring-session and incident lifecycles."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.base import Base
from backend.app.database.repository import (
    finish_monitoring_session,
    get_monitoring_session,
    list_session_incidents,
    start_incident,
    start_monitoring_session,
    update_incident_peak,
    resolve_incident,
)


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


def test_monitoring_session_is_persisted(database: Session) -> None:
    started = datetime(2026, 9, 25, 12, 0, 0)
    created = start_monitoring_session(database, started_at=started)
    loaded = get_monitoring_session(database, created.id)

    assert loaded is not None
    assert loaded.status == "Active"
    assert loaded.started_at == started
    assert loaded.total_incidents == 0


def test_incident_lifecycle_tracks_peak_and_duration(database: Session) -> None:
    started = datetime(2026, 9, 25, 12, 0, 0)
    monitoring = start_monitoring_session(database, started_at=started)
    incident = start_incident(
        database,
        session_id=monitoring.id,
        device_key="cell phone",
        device_name="Mobile Phone",
        confidence=0.62,
        count=1,
        evidence_path="evidence/example.jpg",
        detected_at=started + timedelta(seconds=2),
    )

    update_incident_peak(database, incident.id, confidence=0.91, count=2)
    resolved = resolve_incident(
        database,
        incident.id,
        cleared_at=started + timedelta(seconds=7),
    )

    assert resolved.status == "Resolved"
    assert resolved.maximum_confidence == pytest.approx(0.91)
    assert resolved.maximum_count == 2
    assert resolved.duration_seconds == pytest.approx(5.0)
    assert len(list_session_incidents(database, monitoring.id)) == 1
    assert get_monitoring_session(database, monitoring.id).total_incidents == 1


def test_finishing_session_stops_active_incidents(database: Session) -> None:
    started = datetime(2026, 9, 25, 12, 0, 0)
    monitoring = start_monitoring_session(database, started_at=started)
    incident = start_incident(
        database,
        session_id=monitoring.id,
        device_key="laptop",
        device_name="Laptop / Computer",
        confidence=0.70,
        count=1,
        detected_at=started + timedelta(seconds=1),
    )

    finished = finish_monitoring_session(
        database,
        monitoring.id,
        ended_at=started + timedelta(seconds=6),
    )
    database.refresh(incident)

    assert finished.status == "Completed"
    assert finished.ended_at == started + timedelta(seconds=6)
    assert incident.status == "Stopped"
    assert incident.duration_seconds == pytest.approx(5.0)
