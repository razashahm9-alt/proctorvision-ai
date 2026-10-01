"""Real-time WebSocket transport for webcam monitoring sessions."""

from __future__ import annotations

import json
import time
from typing import Any

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool
from starlette.websockets import WebSocketState

from .detection import get_detector
from ..core.config import settings
from ..core.security import access_cookie_is_valid, websocket_origin_is_allowed
from ..database.base import SessionLocal
from ..services.incident_engine import IncidentEngine


router = APIRouter(tags=["Monitoring"])


def create_database_session():
    """Create one isolated SQLAlchemy session per WebSocket connection."""

    return SessionLocal()


def create_incident_engine(database) -> IncidentEngine:
    """Build the stateful incident engine for one monitoring connection."""

    return IncidentEngine(
        database,
        evidence_directory=settings.evidence_directory,
        confirmation_window=settings.confirmation_window_frames,
        confirmation_required=settings.confirmation_required_frames,
        instant_confirmation_confidence=(
            settings.instant_confirmation_confidence
        ),
        fast_confirmation_confidence=settings.fast_confirmation_confidence,
        fast_confirmation_window=settings.fast_confirmation_window_frames,
        fast_confirmation_required=settings.fast_confirmation_required_frames,
        clear_delay_seconds=settings.incident_clear_delay_seconds,
    )


def decode_frame(payload: bytes) -> np.ndarray:
    """Decode one JPEG, PNG, or WebP binary WebSocket payload."""

    if not payload:
        raise ValueError("The frame payload is empty.")
    encoded = np.frombuffer(payload, dtype=np.uint8)
    frame = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("The binary payload is not a valid image frame.")
    return frame


async def send_error(
    websocket: WebSocket,
    *,
    code: str,
    message: str,
    recoverable: bool,
) -> None:
    """Send a consistent machine-readable WebSocket error."""

    if websocket.client_state == WebSocketState.CONNECTED:
        await websocket.send_json(
            {
                "type": "error",
                "code": code,
                "message": message,
                "recoverable": recoverable,
            }
        )


async def handle_control_message(
    websocket: WebSocket,
    engine: IncidentEngine,
    text: str,
) -> bool:
    """Handle JSON control messages; return True when monitoring must stop."""

    try:
        payload: Any = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        await send_error(
            websocket,
            code="invalid_control_message",
            message="Send control messages as JSON.",
            recoverable=True,
        )
        return False

    if not isinstance(payload, dict):
        await send_error(
            websocket,
            code="invalid_control_message",
            message="The control message must be a JSON object.",
            recoverable=True,
        )
        return False

    message_type = payload.get("type")
    if message_type == "ping":
        await websocket.send_json({"type": "pong"})
        return False
    if message_type == "stop":
        finished = engine.finish()
        await websocket.send_json(
            {
                "type": "session_finished",
                "session_id": finished.id,
                "status": finished.status,
                "total_incidents": finished.total_incidents,
            }
        )
        return True

    await send_error(
        websocket,
        code="unknown_control_message",
        message="Supported control messages are ping and stop.",
        recoverable=True,
    )
    return False


@router.websocket("/ws/monitoring")
async def monitoring_websocket(websocket: WebSocket) -> None:
    """Analyze binary webcam frames and stream incident state as JSON."""

    if not websocket_origin_is_allowed(
        websocket.headers.get("origin"),
        websocket.headers.get("host"),
    ):
        await websocket.close(code=1008, reason="WebSocket origin is not allowed.")
        return
    if not access_cookie_is_valid(
        websocket.cookies.get(settings.access_cookie_name)
    ):
        await websocket.close(code=1008, reason="Supervisor access is required.")
        return

    await websocket.accept()
    database = create_database_session()
    engine = create_incident_engine(database)

    try:
        monitoring_session = engine.start()
        frame_sequence = 0
        await websocket.send_json(
            {
                "type": "session_started",
                "session_id": monitoring_session.id,
                "status": monitoring_session.status,
            }
        )

        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break

            frame_payload = message.get("bytes")
            control_payload = message.get("text")

            if frame_payload is not None:
                processing_started = time.perf_counter()
                if len(frame_payload) > settings.maximum_websocket_frame_bytes:
                    await send_error(
                        websocket,
                        code="frame_too_large",
                        message="Frame exceeds the 3 MB WebSocket limit.",
                        recoverable=True,
                    )
                    continue

                try:
                    frame = decode_frame(frame_payload)
                except ValueError as error:
                    await send_error(
                        websocket,
                        code="invalid_frame",
                        message=str(error),
                        recoverable=True,
                    )
                    continue

                detector = get_detector()
                detection_result = await run_in_threadpool(detector.detect, frame)
                monitoring_state = engine.process_frame(
                    detection_result,
                    frame=frame,
                )
                frame_sequence += 1
                await websocket.send_json(
                    {
                        "type": "frame_result",
                        "sequence": frame_sequence,
                        "server_processing_ms": round(
                            (time.perf_counter() - processing_started) * 1000,
                            2,
                        ),
                        "detection": detection_result.model_dump(mode="json"),
                        "monitoring": monitoring_state.model_dump(mode="json"),
                    }
                )
                continue

            if control_payload is not None:
                should_stop = await handle_control_message(
                    websocket,
                    engine,
                    control_payload,
                )
                if should_stop:
                    await websocket.close(code=1000)
                    break
                continue

            await send_error(
                websocket,
                code="unsupported_message",
                message="Send an image as binary data or a JSON control message.",
                recoverable=True,
            )

    except WebSocketDisconnect:
        pass
    except (FileNotFoundError, ImportError, RuntimeError, OSError) as error:
        await send_error(
            websocket,
            code="monitoring_unavailable",
            message=str(error),
            recoverable=False,
        )
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=1011)
    finally:
        if engine.started:
            engine.finish()
        database.close()
