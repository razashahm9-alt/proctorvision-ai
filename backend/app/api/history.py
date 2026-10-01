"""REST endpoints for reviewing sessions, evidence, and CSV audit logs."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core.config import settings
from ..database.base import get_db
from ..database.models import Incident, MonitoringSession
from ..database.repository import (
    count_monitoring_sessions,
    get_monitoring_session,
    list_monitoring_sessions,
    list_session_incidents,
)


router = APIRouter(prefix="/history", tags=["Session History"])


class IncidentRecord(BaseModel):
    id: str
    session_id: str
    device_key: str
    device_name: str
    status: str
    maximum_confidence: float = Field(ge=0.0, le=1.0)
    maximum_count: int = Field(ge=1)
    detected_at: datetime
    cleared_at: datetime | None
    duration_seconds: float | None
    evidence_available: bool
    evidence_url: str | None


class SessionSummary(BaseModel):
    id: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: float | None
    total_incidents: int = Field(ge=0)
    detail_url: str
    csv_url: str


class SessionDetail(SessionSummary):
    incidents: list[IncidentRecord]


class SessionListResponse(BaseModel):
    items: list[SessionSummary]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


def _utc(value: datetime | None) -> datetime | None:
    """Attach UTC to the intentionally naive SQLite timestamps."""

    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _iso_utc(value: datetime | None) -> str:
    converted = _utc(value)
    return converted.isoformat().replace("+00:00", "Z") if converted else ""


def _session_duration(monitoring_session: MonitoringSession) -> float | None:
    if monitoring_session.ended_at is None:
        return None
    return max(
        0.0,
        (monitoring_session.ended_at - monitoring_session.started_at).total_seconds(),
    )


def _evidence_path(incident: Incident) -> Path | None:
    if not incident.evidence_path:
        return None
    path = Path(incident.evidence_path)
    try:
        path.resolve().relative_to(settings.evidence_directory.resolve())
    except ValueError:
        return None
    return path if path.is_file() else None


def _incident_record(incident: Incident) -> IncidentRecord:
    evidence = _evidence_path(incident)
    return IncidentRecord(
        id=incident.id,
        session_id=incident.session_id,
        device_key=incident.device_key,
        device_name=incident.device_name,
        status=incident.status,
        maximum_confidence=incident.maximum_confidence,
        maximum_count=incident.maximum_count,
        detected_at=_utc(incident.detected_at),
        cleared_at=_utc(incident.cleared_at),
        duration_seconds=incident.duration_seconds,
        evidence_available=evidence is not None,
        evidence_url=(
            f"/api/history/incidents/{incident.id}/evidence"
            if evidence is not None
            else None
        ),
    )


def _session_summary(monitoring_session: MonitoringSession) -> SessionSummary:
    session_id = monitoring_session.id
    return SessionSummary(
        id=session_id,
        status=monitoring_session.status,
        started_at=_utc(monitoring_session.started_at),
        ended_at=_utc(monitoring_session.ended_at),
        duration_seconds=_session_duration(monitoring_session),
        total_incidents=monitoring_session.total_incidents,
        detail_url=f"/api/history/sessions/{session_id}",
        csv_url=f"/api/history/sessions/{session_id}/export.csv",
    )


def _require_session(database: Session, session_id: str) -> MonitoringSession:
    monitoring_session = get_monitoring_session(database, session_id)
    if monitoring_session is None:
        raise HTTPException(status_code=404, detail="Monitoring session not found.")
    return monitoring_session


@router.get("/sessions", response_model=SessionListResponse)
def get_sessions(
    database: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SessionListResponse:
    """List newest monitoring sessions first."""

    sessions = list_monitoring_sessions(database, limit=limit, offset=offset)
    return SessionListResponse(
        items=[_session_summary(item) for item in sessions],
        total=count_monitoring_sessions(database),
        limit=limit,
        offset=offset,
    )


@router.get("/sessions/{session_id}", response_model=SessionDetail)
def get_session(
    session_id: str,
    database: Annotated[Session, Depends(get_db)],
) -> SessionDetail:
    """Return one session and its complete incident timeline."""

    monitoring_session = _require_session(database, session_id)
    incidents = list_session_incidents(database, session_id)
    return SessionDetail(
        **_session_summary(monitoring_session).model_dump(),
        incidents=[_incident_record(item) for item in incidents],
    )


@router.get("/incidents/{incident_id}/evidence")
def get_incident_evidence(
    incident_id: str,
    database: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    """Serve the annotated evidence image for one incident."""

    incident = database.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found.")
    evidence = _evidence_path(incident)
    if evidence is None:
        raise HTTPException(status_code=404, detail="Evidence image not found.")
    return FileResponse(evidence, media_type="image/jpeg")


@router.get("/sessions/{session_id}/export.csv")
def export_session_csv(
    session_id: str,
    database: Annotated[Session, Depends(get_db)],
) -> Response:
    """Download a Windows/Excel-friendly CSV audit log for one session."""

    monitoring_session = _require_session(database, session_id)
    incidents = list_session_incidents(database, session_id)
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        [
            "Incident ID",
            "Session ID",
            "Device",
            "Status",
            "Detected At (UTC)",
            "Cleared At (UTC)",
            "Duration (seconds)",
            "Maximum Confidence (%)",
            "Maximum Device Count",
            "Evidence File",
        ]
    )
    for incident in incidents:
        evidence = _evidence_path(incident)
        writer.writerow(
            [
                incident.id,
                monitoring_session.id,
                incident.device_name,
                incident.status,
                _iso_utc(incident.detected_at),
                _iso_utc(incident.cleared_at),
                "" if incident.duration_seconds is None else f"{incident.duration_seconds:.2f}",
                f"{incident.maximum_confidence * 100:.2f}",
                incident.maximum_count,
                evidence.name if evidence is not None else "",
            ]
        )

    content = "\ufeff" + output.getvalue()
    headers = {
        "Content-Disposition": f'attachment; filename="{session_id}.csv"',
        "X-ProctorVision-Session-Status": monitoring_session.status,
    }
    return Response(
        content=content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers=headers,
    )
