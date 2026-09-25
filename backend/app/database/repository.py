"""Reusable database operations for sessions and incidents."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Incident, MonitoringSession, utc_now


def create_session_id(started_at: datetime | None = None) -> str:
    timestamp = started_at or utc_now()
    return f"SESSION-{timestamp:%Y%m%d-%H%M%S}-{uuid4().hex[:8].upper()}"


def create_incident_id(device_key: str, detected_at: datetime | None = None) -> str:
    timestamp = detected_at or utc_now()
    device = device_key.replace(" ", "-").upper()
    return f"EVT-{timestamp:%Y%m%d-%H%M%S-%f}-{device}"


def start_monitoring_session(
    database: Session,
    *,
    started_at: datetime | None = None,
    session_id: str | None = None,
) -> MonitoringSession:
    started = started_at or utc_now()
    monitoring_session = MonitoringSession(
        id=session_id or create_session_id(started),
        status="Active",
        started_at=started,
        total_incidents=0,
    )
    database.add(monitoring_session)
    database.commit()
    database.refresh(monitoring_session)
    return monitoring_session


def get_monitoring_session(
    database: Session, session_id: str
) -> MonitoringSession | None:
    return database.get(MonitoringSession, session_id)


def list_monitoring_sessions(database: Session) -> list[MonitoringSession]:
    statement = select(MonitoringSession).order_by(
        MonitoringSession.started_at.desc()
    )
    return list(database.scalars(statement))


def start_incident(
    database: Session,
    *,
    session_id: str,
    device_key: str,
    device_name: str,
    confidence: float,
    count: int,
    evidence_path: str = "",
    detected_at: datetime | None = None,
    incident_id: str | None = None,
) -> Incident:
    monitoring_session = get_monitoring_session(database, session_id)
    if monitoring_session is None:
        raise ValueError(f"Monitoring session does not exist: {session_id}")
    if monitoring_session.status != "Active":
        raise ValueError(f"Monitoring session is not active: {session_id}")

    detected = detected_at or utc_now()
    incident = Incident(
        id=incident_id or create_incident_id(device_key, detected),
        session_id=session_id,
        device_key=device_key,
        device_name=device_name,
        status="Active",
        maximum_confidence=confidence,
        maximum_count=max(1, count),
        detected_at=detected,
        evidence_path=evidence_path,
    )
    monitoring_session.total_incidents += 1
    database.add(incident)
    database.commit()
    database.refresh(incident)
    return incident


def update_incident_peak(
    database: Session,
    incident_id: str,
    *,
    confidence: float,
    count: int,
) -> Incident:
    incident = database.get(Incident, incident_id)
    if incident is None:
        raise ValueError(f"Incident does not exist: {incident_id}")
    if incident.status != "Active":
        return incident

    incident.maximum_confidence = max(incident.maximum_confidence, confidence)
    incident.maximum_count = max(incident.maximum_count, count)
    database.commit()
    database.refresh(incident)
    return incident


def resolve_incident(
    database: Session,
    incident_id: str,
    *,
    cleared_at: datetime | None = None,
    status: str = "Resolved",
) -> Incident:
    incident = database.get(Incident, incident_id)
    if incident is None:
        raise ValueError(f"Incident does not exist: {incident_id}")
    if incident.status != "Active":
        return incident

    cleared = cleared_at or utc_now()
    incident.cleared_at = cleared
    incident.duration_seconds = max(
        0.0, (cleared - incident.detected_at).total_seconds()
    )
    incident.status = status
    database.commit()
    database.refresh(incident)
    return incident


def list_session_incidents(database: Session, session_id: str) -> list[Incident]:
    statement = (
        select(Incident)
        .where(Incident.session_id == session_id)
        .order_by(Incident.detected_at.asc())
    )
    return list(database.scalars(statement))


def finish_monitoring_session(
    database: Session,
    session_id: str,
    *,
    ended_at: datetime | None = None,
    status: str = "Completed",
) -> MonitoringSession:
    monitoring_session = get_monitoring_session(database, session_id)
    if monitoring_session is None:
        raise ValueError(f"Monitoring session does not exist: {session_id}")

    ended = ended_at or utc_now()
    active_statement = select(Incident).where(
        Incident.session_id == session_id,
        Incident.status == "Active",
    )
    for incident in database.scalars(active_statement):
        incident.cleared_at = ended
        incident.duration_seconds = max(
            0.0, (ended - incident.detected_at).total_seconds()
        )
        incident.status = "Stopped"

    monitoring_session.ended_at = ended
    monitoring_session.status = status
    database.commit()
    database.refresh(monitoring_session)
    return monitoring_session
