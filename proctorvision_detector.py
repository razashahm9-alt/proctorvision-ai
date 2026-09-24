"""Standalone ProctorVision AI webcam detector.

This prototype detects prohibited electronic devices with YOLO11s, confirms
violations across multiple frames, sounds an alert, saves evidence images,
logs events to CSV, and obscures the visible preview while inference continues.
"""

from __future__ import annotations

import csv
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import cv2
from ultralytics import YOLO

try:
    import winsound
except ImportError:  # pragma: no cover - Windows is the target platform.
    winsound = None


PROJECT_ROOT = Path(__file__).resolve().parent
MODEL_PATH = PROJECT_ROOT / "yolo11s.pt"
EVIDENCE_DIR = PROJECT_ROOT / "evidence"
LOG_DIR = PROJECT_ROOT / "logs"
EVENT_LOG_PATH = LOG_DIR / "detection_events.csv"

CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
DISPLAY_WIDTH = 960
DISPLAY_HEIGHT = 720
IMAGE_SIZE = 416
RAW_CONFIDENCE = 0.25
IOU_THRESHOLD = 0.50

CONFIRMATION_WINDOW = 5
CONFIRMATION_HITS = 3
CLEAR_DELAY_SECONDS = 2.0

DISPLAY_NAMES = {
    "cell phone": "Mobile Phone",
    "laptop": "Laptop / Computer",
    "tv": "TV / LCD / Monitor",
}

CLASS_THRESHOLDS = {
    "cell phone": 0.30,
    "laptop": 0.35,
    "tv": 0.35,
}

CLASS_COLORS = {
    "cell phone": (0, 220, 255),
    "laptop": (255, 180, 0),
    "tv": (0, 80, 255),
}

CSV_FIELDS = [
    "event_id",
    "session_id",
    "device",
    "maximum_confidence",
    "maximum_count",
    "detected_at",
    "cleared_at",
    "duration_seconds",
    "evidence_path",
    "status",
]


@dataclass
class DeviceState:
    history: deque[bool] = field(
        default_factory=lambda: deque(maxlen=CONFIRMATION_WINDOW)
    )
    active: bool = False
    event_id: str | None = None
    started_at: datetime | None = None
    started_monotonic: float = 0.0
    last_seen_monotonic: float = 0.0
    max_confidence: float = 0.0
    max_count: int = 0
    evidence_path: str = ""


class EventLogger:
    """Maintain one current CSV row per event, including active events."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.rows: list[dict[str, str]] = []
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if self.path.exists():
            with self.path.open("r", newline="", encoding="utf-8") as handle:
                self.rows = list(csv.DictReader(handle))

    def create(self, row: dict[str, str]) -> None:
        self.rows.append(row)
        self._write()

    def update(self, event_id: str, updates: dict[str, str]) -> None:
        for row in self.rows:
            if row["event_id"] == event_id:
                row.update(updates)
                self._write()
                return

    def _write(self) -> None:
        with self.path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(self.rows)


def play_alert() -> None:
    """Play the alert without blocking video inference."""

    if winsound is not None:
        winsound.Beep(1500, 550)
    else:
        print("\a", end="", flush=True)


def start_alert_thread() -> None:
    threading.Thread(target=play_alert, daemon=True).start()


def open_camera() -> cv2.VideoCapture:
    """Open the webcam with a Windows-friendly backend and safe fallback."""

    camera = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    if not camera.isOpened():
        camera.release()
        camera = cv2.VideoCapture(CAMERA_INDEX)

    if not camera.isOpened():
        raise RuntimeError(
            "Unable to open webcam 0. Close Camera, Zoom, Teams, or other apps "
            "that may be using it, then try again."
        )

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return camera


def draw_detection(
    frame,
    coordinates: tuple[int, int, int, int],
    class_name: str,
    confidence: float,
) -> None:
    x1, y1, x2, y2 = coordinates
    color = CLASS_COLORS[class_name]
    label = f"{DISPLAY_NAMES[class_name]}  {confidence:.0%}"

    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    (text_width, text_height), _ = cv2.getTextSize(
        label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2
    )
    label_top = max(y1, text_height + 12)
    cv2.rectangle(
        frame,
        (x1, label_top - text_height - 12),
        (x1 + text_width + 10, label_top),
        color,
        -1,
    )
    cv2.putText(
        frame,
        label,
        (x1 + 5, label_top - 6),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (15, 15, 15),
        2,
        cv2.LINE_AA,
    )


def draw_status_bar(frame, status: str, fps: float, session_id: str) -> None:
    is_violation = status.startswith("VIOLATION")
    color = (0, 0, 210) if is_violation else (20, 155, 70)

    cv2.rectangle(frame, (0, 0), (frame.shape[1], 58), (18, 24, 34), -1)
    cv2.circle(frame, (24, 29), 9, color, -1)
    cv2.putText(
        frame,
        status,
        (44, 38),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.72,
        (245, 245, 245),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        f"AI FPS: {fps:.1f}",
        (frame.shape[1] - 155, 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (210, 220, 230),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        session_id,
        (frame.shape[1] - 155, 47),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.40,
        (155, 175, 195),
        1,
        cv2.LINE_AA,
    )


def build_blocked_preview(frame, active_devices: list[str]) -> object:
    """Obscure the visible preview while keeping the source frame available."""

    blocked = cv2.GaussianBlur(frame, (51, 51), 0)
    tint = blocked.copy()
    cv2.rectangle(tint, (0, 0), (blocked.shape[1], blocked.shape[0]), (0, 0, 120), -1)
    blocked = cv2.addWeighted(tint, 0.38, blocked, 0.62, 0)

    panel_left = 45
    panel_right = blocked.shape[1] - 45
    panel_top = blocked.shape[0] // 2 - 85
    panel_bottom = blocked.shape[0] // 2 + 90
    cv2.rectangle(
        blocked,
        (panel_left, panel_top),
        (panel_right, panel_bottom),
        (18, 18, 28),
        -1,
    )
    cv2.rectangle(
        blocked,
        (panel_left, panel_top),
        (panel_right, panel_bottom),
        (0, 45, 235),
        3,
    )

    cv2.putText(
        blocked,
        "PROHIBITED DEVICE DETECTED",
        (75, panel_top + 48),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.78,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    device_text = ", ".join(active_devices)
    cv2.putText(
        blocked,
        device_text,
        (75, panel_top + 91),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.64,
        (80, 190, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        blocked,
        "Preview restricted - background monitoring remains active",
        (75, panel_top + 133),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (205, 215, 225),
        1,
        cv2.LINE_AA,
    )
    return blocked


def create_event_id(device_key: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
    return f"EVT-{timestamp}-{device_key.replace(' ', '-').upper()}"


def save_evidence(frame, event_id: str, session_id: str) -> str:
    session_directory = EVIDENCE_DIR / session_id
    session_directory.mkdir(parents=True, exist_ok=True)
    path = session_directory / f"{event_id}.jpg"
    if not cv2.imwrite(str(path), frame):
        raise RuntimeError(f"Unable to save evidence image: {path}")
    return str(path.relative_to(PROJECT_ROOT))


def activate_event(
    state: DeviceState,
    class_name: str,
    annotated_frame,
    session_id: str,
    logger: EventLogger,
    confidence: float,
    count: int,
    now_monotonic: float,
) -> None:
    now = datetime.now()
    event_id = create_event_id(class_name)
    evidence_path = save_evidence(annotated_frame, event_id, session_id)

    state.active = True
    state.event_id = event_id
    state.started_at = now
    state.started_monotonic = now_monotonic
    state.last_seen_monotonic = now_monotonic
    state.max_confidence = confidence
    state.max_count = count
    state.evidence_path = evidence_path

    logger.create(
        {
            "event_id": event_id,
            "session_id": session_id,
            "device": DISPLAY_NAMES[class_name],
            "maximum_confidence": f"{confidence:.4f}",
            "maximum_count": str(count),
            "detected_at": now.isoformat(timespec="seconds"),
            "cleared_at": "",
            "duration_seconds": "",
            "evidence_path": evidence_path,
            "status": "Active",
        }
    )
    start_alert_thread()
    print(
        f"[{now:%H:%M:%S}] VIOLATION STARTED: {DISPLAY_NAMES[class_name]} "
        f"({confidence:.0%})"
    )


def close_event(
    state: DeviceState,
    class_name: str,
    logger: EventLogger,
    now_monotonic: float,
    status: str = "Resolved",
) -> None:
    if not state.active or state.event_id is None or state.started_at is None:
        return

    ended_at = datetime.now()
    duration = max(0.0, now_monotonic - state.started_monotonic)
    logger.update(
        state.event_id,
        {
            "maximum_confidence": f"{state.max_confidence:.4f}",
            "maximum_count": str(state.max_count),
            "cleared_at": ended_at.isoformat(timespec="seconds"),
            "duration_seconds": f"{duration:.2f}",
            "status": status,
        },
    )
    print(
        f"[{ended_at:%H:%M:%S}] VIOLATION {status.upper()}: "
        f"{DISPLAY_NAMES[class_name]} ({duration:.1f}s)"
    )

    state.active = False
    state.event_id = None
    state.started_at = None
    state.started_monotonic = 0.0
    state.last_seen_monotonic = 0.0
    state.max_confidence = 0.0
    state.max_count = 0
    state.evidence_path = ""
    state.history.clear()


def main() -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    session_id = f"SESSION-{datetime.now():%Y%m%d-%H%M%S}"
    logger = EventLogger(EVENT_LOG_PATH)

    model_source = str(MODEL_PATH) if MODEL_PATH.exists() else "yolo11s.pt"
    print(f"Loading model: {model_source}")
    model = YOLO(model_source)

    target_ids = {
        int(class_id): class_name
        for class_id, class_name in model.names.items()
        if class_name in DISPLAY_NAMES
    }
    missing_classes = set(DISPLAY_NAMES) - set(target_ids.values())
    if missing_classes:
        raise RuntimeError(
            "Model is missing required classes: " + ", ".join(sorted(missing_classes))
        )

    states = {class_name: DeviceState() for class_name in DISPLAY_NAMES}
    camera = open_camera()
    fps = 0.0
    previous_time = time.perf_counter()

    print(f"Monitoring started: {session_id}")
    print("Press Q or Esc in the detector window to stop safely.")

    try:
        while True:
            success, frame = camera.read()
            if not success:
                raise RuntimeError("The webcam stopped returning frames.")

            results = model.predict(
                source=frame,
                imgsz=IMAGE_SIZE,
                conf=RAW_CONFIDENCE,
                iou=IOU_THRESHOLD,
                classes=list(target_ids),
                device="cpu",
                max_det=10,
                verbose=False,
            )

            detections: dict[str, list[tuple[float, tuple[int, int, int, int]]]] = {
                class_name: [] for class_name in DISPLAY_NAMES
            }
            annotated = frame.copy()
            result = results[0]

            if result.boxes is not None:
                for box in result.boxes:
                    class_id = int(box.cls[0].item())
                    class_name = target_ids.get(class_id)
                    if class_name is None:
                        continue

                    confidence = float(box.conf[0].item())
                    if confidence < CLASS_THRESHOLDS[class_name]:
                        continue

                    x1, y1, x2, y2 = (
                        int(value) for value in box.xyxy[0].tolist()
                    )
                    coordinates = (x1, y1, x2, y2)
                    detections[class_name].append((confidence, coordinates))
                    draw_detection(annotated, coordinates, class_name, confidence)

            now_monotonic = time.perf_counter()

            for class_name, state in states.items():
                class_detections = detections[class_name]
                present = bool(class_detections)
                state.history.append(present)

                if present:
                    confidence = max(item[0] for item in class_detections)
                    count = len(class_detections)
                    state.last_seen_monotonic = now_monotonic
                    state.max_confidence = max(state.max_confidence, confidence)
                    state.max_count = max(state.max_count, count)

                    if (
                        not state.active
                        and len(state.history) == CONFIRMATION_WINDOW
                        and sum(state.history) >= CONFIRMATION_HITS
                    ):
                        activate_event(
                            state,
                            class_name,
                            annotated,
                            session_id,
                            logger,
                            confidence,
                            count,
                            now_monotonic,
                        )
                elif (
                    state.active
                    and now_monotonic - state.last_seen_monotonic
                    >= CLEAR_DELAY_SECONDS
                ):
                    close_event(
                        state,
                        class_name,
                        logger,
                        now_monotonic,
                        status="Resolved",
                    )

            current_time = time.perf_counter()
            instantaneous_fps = 1.0 / max(current_time - previous_time, 1e-6)
            previous_time = current_time
            fps = instantaneous_fps if fps == 0.0 else (0.90 * fps + 0.10 * instantaneous_fps)

            active_devices = [
                DISPLAY_NAMES[class_name]
                for class_name, state in states.items()
                if state.active
            ]

            if active_devices:
                display_frame = build_blocked_preview(annotated, active_devices)
                status = "VIOLATION ACTIVE"
            else:
                display_frame = annotated
                status = "MONITORING - SAFE"

            draw_status_bar(display_frame, status, fps, session_id)
            cv2.putText(
                display_frame,
                "Press Q or Esc to stop",
                (18, display_frame.shape[0] - 18),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (230, 235, 240),
                1,
                cv2.LINE_AA,
            )

            display_frame = cv2.resize(
                display_frame,
                (DISPLAY_WIDTH, DISPLAY_HEIGHT),
                interpolation=cv2.INTER_LINEAR,
            )
            cv2.imshow("ProctorVision AI - Standalone Detector", display_frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break

    finally:
        stopped_at = time.perf_counter()
        for class_name, state in states.items():
            if state.active:
                close_event(
                    state,
                    class_name,
                    logger,
                    stopped_at,
                    status="Stopped",
                )
        camera.release()
        cv2.destroyAllWindows()
        print("Monitoring stopped safely.")
        print(f"Event log: {EVENT_LOG_PATH}")
        print(f"Evidence directory: {EVIDENCE_DIR}")


if __name__ == "__main__":
    main()
