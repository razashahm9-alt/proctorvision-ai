"""Temporal confirmation and persistent incident management."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database.models import MonitoringSession, utc_now
from ..database.repository import (
    create_incident_id,
    finish_monitoring_session,
    resolve_incident,
    start_incident,
    start_monitoring_session,
    update_incident_peak,
)
from ..detection.constants import DISPLAY_NAMES
from ..detection.schemas import DetectionItem, FrameDetectionResponse
from .evidence import EvidenceWriter


class IncidentEvent(BaseModel):
    """A device incident transition produced while processing a frame."""

    event_type: str
    incident_id: str
    device_key: str
    device_name: str
    confidence: float
    count: int
    evidence_path: str = ""
    alert_message: str


class ActiveIncidentState(BaseModel):
    """Current device state used to render a persistent blocking overlay."""

    incident_id: str
    device_key: str
    device_name: str
    confidence: float
    count: int
    evidence_path: str = ""
    alert_message: str


class MonitoringFrameState(BaseModel):
    """Frontend-ready state after one detection result is processed."""

    session_id: str
    should_block_preview: bool
    play_alert_sound: bool
    active_incident_ids: list[str]
    active_incidents: list[ActiveIncidentState]
    events: list[IncidentEvent]


@dataclass(slots=True)
class DeviceTracker:
    observations: deque[bool]
    active_incident_id: str | None = None
    evidence_path: str = ""
    peak_confidence: float = 0.0
    peak_count: int = 0
    missing_since: datetime | None = None


@dataclass(frozen=True, slots=True)
class DeviceFrameSummary:
    detections: list[DetectionItem]
    confidence: float
    count: int


class IncidentEngine:
    """Turn noisy frame detections into stable, database-backed incidents."""

    def __init__(
        self,
        database: Session,
        *,
        evidence_directory: Path,
        confirmation_window: int = 5,
        confirmation_required: int = 3,
        clear_delay_seconds: float = 2.0,
    ) -> None:
        if confirmation_window < 1:
            raise ValueError("confirmation_window must be at least 1")
        if not 1 <= confirmation_required <= confirmation_window:
            raise ValueError(
                "confirmation_required must be within confirmation_window"
            )
        if clear_delay_seconds < 0:
            raise ValueError("clear_delay_seconds cannot be negative")

        self.database = database
        self.confirmation_window = confirmation_window
        self.confirmation_required = confirmation_required
        self.clear_delay_seconds = clear_delay_seconds
        self.evidence_writer = EvidenceWriter(evidence_directory)
        self.session: MonitoringSession | None = None
        self.trackers = {
            device_key: DeviceTracker(deque(maxlen=confirmation_window))
            for device_key in DISPLAY_NAMES
        }

    @property
    def started(self) -> bool:
        return self.session is not None and self.session.status == "Active"

    def start(self, *, started_at: datetime | None = None) -> MonitoringSession:
        if self.started:
            raise RuntimeError("The monitoring session is already active.")
        self.session = start_monitoring_session(
            self.database,
            started_at=started_at,
        )
        return self.session

    def process_frame(
        self,
        detection_result: FrameDetectionResponse,
        *,
        frame: np.ndarray | None = None,
        observed_at: datetime | None = None,
    ) -> MonitoringFrameState:
        if not self.started or self.session is None:
            raise RuntimeError("Start a monitoring session before processing frames.")

        observed = observed_at or utc_now()
        summaries = self._summarize(detection_result.detections)
        events: list[IncidentEvent] = []

        for device_key, device_name in DISPLAY_NAMES.items():
            tracker = self.trackers[device_key]
            summary = summaries.get(device_key)
            present = summary is not None
            tracker.observations.append(present)

            if tracker.active_incident_id is not None:
                if present and summary is not None:
                    tracker.missing_since = None
                    if (
                        summary.confidence > tracker.peak_confidence
                        or summary.count > tracker.peak_count
                    ):
                        update_incident_peak(
                            self.database,
                            tracker.active_incident_id,
                            confidence=summary.confidence,
                            count=summary.count,
                        )
                        tracker.peak_confidence = max(
                            tracker.peak_confidence, summary.confidence
                        )
                        tracker.peak_count = max(tracker.peak_count, summary.count)
                else:
                    self._handle_missing(
                        device_key=device_key,
                        device_name=device_name,
                        tracker=tracker,
                        observed_at=observed,
                        events=events,
                    )
                continue

            if (
                summary is not None
                and sum(tracker.observations) >= self.confirmation_required
            ):
                event = self._start_incident(
                    device_key=device_key,
                    device_name=device_name,
                    tracker=tracker,
                    summary=summary,
                    frame=frame,
                    observed_at=observed,
                )
                events.append(event)

        active_ids = [
            tracker.active_incident_id
            for tracker in self.trackers.values()
            if tracker.active_incident_id is not None
        ]
        active_incidents = [
            ActiveIncidentState(
                incident_id=tracker.active_incident_id,
                device_key=device_key,
                device_name=DISPLAY_NAMES[device_key],
                confidence=tracker.peak_confidence,
                count=tracker.peak_count,
                evidence_path=tracker.evidence_path,
                alert_message=f"{DISPLAY_NAMES[device_key]} Detected",
            )
            for device_key, tracker in self.trackers.items()
            if tracker.active_incident_id is not None
        ]
        return MonitoringFrameState(
            session_id=self.session.id,
            should_block_preview=bool(active_ids),
            play_alert_sound=any(
                event.event_type == "started" for event in events
            ),
            active_incident_ids=active_ids,
            active_incidents=active_incidents,
            events=events,
        )

    def finish(self, *, ended_at: datetime | None = None) -> MonitoringSession:
        if not self.started or self.session is None:
            raise RuntimeError("There is no active monitoring session to finish.")

        finished = finish_monitoring_session(
            self.database,
            self.session.id,
            ended_at=ended_at,
        )
        for tracker in self.trackers.values():
            self._reset_tracker(tracker)
        self.session = finished
        return finished

    @staticmethod
    def _summarize(
        detections: list[DetectionItem],
    ) -> dict[str, DeviceFrameSummary]:
        grouped: dict[str, list[DetectionItem]] = {}
        for detection in detections:
            if detection.class_name in DISPLAY_NAMES:
                grouped.setdefault(detection.class_name, []).append(detection)

        return {
            device_key: DeviceFrameSummary(
                detections=items,
                confidence=max(item.confidence for item in items),
                count=len(items),
            )
            for device_key, items in grouped.items()
        }

    def _start_incident(
        self,
        *,
        device_key: str,
        device_name: str,
        tracker: DeviceTracker,
        summary: DeviceFrameSummary,
        frame: np.ndarray | None,
        observed_at: datetime,
    ) -> IncidentEvent:
        assert self.session is not None
        incident_id = create_incident_id(device_key, observed_at)
        evidence_path = ""
        if frame is not None:
            evidence_path = self.evidence_writer.save(
                frame=frame,
                session_id=self.session.id,
                incident_id=incident_id,
                device_key=device_key,
                detections=summary.detections,
            )

        incident = start_incident(
            self.database,
            session_id=self.session.id,
            device_key=device_key,
            device_name=device_name,
            confidence=summary.confidence,
            count=summary.count,
            evidence_path=evidence_path,
            detected_at=observed_at,
            incident_id=incident_id,
        )
        tracker.active_incident_id = incident.id
        tracker.evidence_path = evidence_path
        tracker.peak_confidence = summary.confidence
        tracker.peak_count = summary.count
        tracker.missing_since = None

        return IncidentEvent(
            event_type="started",
            incident_id=incident.id,
            device_key=device_key,
            device_name=device_name,
            confidence=summary.confidence,
            count=summary.count,
            evidence_path=evidence_path,
            alert_message=f"{device_name} Detected",
        )

    def _handle_missing(
        self,
        *,
        device_key: str,
        device_name: str,
        tracker: DeviceTracker,
        observed_at: datetime,
        events: list[IncidentEvent],
    ) -> None:
        if tracker.missing_since is None:
            tracker.missing_since = observed_at
            return
        missing_seconds = (observed_at - tracker.missing_since).total_seconds()
        if missing_seconds < self.clear_delay_seconds:
            return

        assert tracker.active_incident_id is not None
        incident_id = tracker.active_incident_id
        resolve_incident(
            self.database,
            incident_id,
            cleared_at=observed_at,
        )
        events.append(
            IncidentEvent(
                event_type="resolved",
                incident_id=incident_id,
                device_key=device_key,
                device_name=device_name,
                confidence=tracker.peak_confidence,
                count=tracker.peak_count,
                evidence_path=tracker.evidence_path,
                alert_message=f"{device_name} Removed",
            )
        )
        self._reset_tracker(tracker)

    @staticmethod
    def _reset_tracker(tracker: DeviceTracker) -> None:
        tracker.observations.clear()
        tracker.active_incident_id = None
        tracker.evidence_path = ""
        tracker.peak_confidence = 0.0
        tracker.peak_count = 0
        tracker.missing_since = None
