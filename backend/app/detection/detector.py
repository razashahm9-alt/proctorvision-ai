"""Reusable YOLO service for prohibited-device detection."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any

import numpy as np
from ultralytics import YOLO

from ..core.config import Settings
from .constants import CLASS_THRESHOLDS, DISPLAY_NAMES
from .schemas import BoundingBox, DetectionItem, FrameDetectionResponse


@dataclass(frozen=True, slots=True)
class BoxMetrics:
    area_ratio: float
    width_ratio: float
    aspect_ratio: float


def calculate_box_metrics(
    box: tuple[int, int, int, int], frame_shape: tuple[int, ...]
) -> BoxMetrics:
    """Calculate normalized box measurements used by geometry filters."""

    frame_height, frame_width = frame_shape[:2]
    x1, y1, x2, y2 = box
    box_width = max(0, x2 - x1)
    box_height = max(0, y2 - y1)
    frame_area = max(1, frame_width * frame_height)

    return BoxMetrics(
        area_ratio=(box_width * box_height) / frame_area,
        width_ratio=box_width / max(1, frame_width),
        aspect_ratio=box_width / max(1, box_height),
    )


def is_plausible_detection(
    class_name: str,
    box: tuple[int, int, int, int],
    frame_shape: tuple[int, ...],
) -> bool:
    """Reject boxes whose geometry is implausible for their predicted class.

    The laptop rules specifically remove the narrow edge boxes observed in the
    validated standalone session while retaining ordinary open-laptop shapes.
    """

    x1, y1, x2, y2 = box
    if x2 <= x1 or y2 <= y1:
        return False

    metrics = calculate_box_metrics(box, frame_shape)

    if class_name == "cell phone":
        return metrics.area_ratio >= 0.0015

    if class_name == "laptop":
        return (
            metrics.area_ratio >= 0.015
            and metrics.width_ratio >= 0.12
            and metrics.aspect_ratio >= 0.60
        )

    if class_name == "tv":
        return (
            metrics.area_ratio >= 0.020
            and metrics.width_ratio >= 0.15
            and metrics.aspect_ratio >= 0.80
        )

    return False


class DeviceDetector:
    """Load YOLO once and provide thread-safe frame inference."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._model: Any | None = None
        self._target_ids: dict[int, str] = {}
        self._load_lock = threading.Lock()
        self._inference_lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def status(self) -> dict[str, object]:
        return {
            "loaded": self.loaded,
            "model_path": str(self.settings.model_path),
            "model_file_exists": self.settings.model_path.exists(),
            "required_classes": list(DISPLAY_NAMES.values()),
        }

    def load(self) -> None:
        """Load and validate the configured model exactly once."""

        if self.loaded:
            return

        with self._load_lock:
            if self.loaded:
                return

            if not self.settings.model_path.exists():
                raise FileNotFoundError(
                    f"YOLO model not found: {self.settings.model_path}"
                )

            model = YOLO(str(self.settings.model_path))
            target_ids = {
                int(class_id): class_name
                for class_id, class_name in model.names.items()
                if class_name in DISPLAY_NAMES
            }
            missing_classes = set(DISPLAY_NAMES) - set(target_ids.values())
            if missing_classes:
                missing = ", ".join(sorted(missing_classes))
                raise RuntimeError(f"Model is missing required classes: {missing}")

            self._model = model
            self._target_ids = target_ids

    def detect(self, frame: np.ndarray) -> FrameDetectionResponse:
        """Run inference on one decoded BGR image frame."""

        if frame.size == 0:
            raise ValueError("The supplied image frame is empty.")

        self.load()
        frame_height, frame_width = frame.shape[:2]

        started = time.perf_counter()
        with self._inference_lock:
            results = self._model.predict(
                source=frame,
                imgsz=self.settings.image_size,
                conf=self.settings.raw_confidence,
                iou=self.settings.iou_threshold,
                classes=list(self._target_ids),
                device=self.settings.device,
                max_det=self.settings.maximum_detections,
                verbose=False,
            )
        inference_ms = (time.perf_counter() - started) * 1000

        detections: list[DetectionItem] = []
        result = results[0]

        if result.boxes is not None:
            for result_box in result.boxes:
                class_id = int(result_box.cls[0].item())
                class_name = self._target_ids.get(class_id)
                if class_name is None:
                    continue

                confidence = float(result_box.conf[0].item())
                if confidence < CLASS_THRESHOLDS[class_name]:
                    continue

                raw = [int(value) for value in result_box.xyxy[0].tolist()]
                x1 = max(0, min(frame_width - 1, raw[0]))
                y1 = max(0, min(frame_height - 1, raw[1]))
                x2 = max(0, min(frame_width, raw[2]))
                y2 = max(0, min(frame_height, raw[3]))
                coordinates = (x1, y1, x2, y2)

                if not is_plausible_detection(
                    class_name, coordinates, frame.shape
                ):
                    continue

                detections.append(
                    DetectionItem(
                        class_name=class_name,
                        display_name=DISPLAY_NAMES[class_name],
                        confidence=round(confidence, 4),
                        box=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
                    )
                )

        detections.sort(key=lambda item: item.confidence, reverse=True)
        return FrameDetectionResponse(
            detected=bool(detections),
            device_count=len(detections),
            image_width=frame_width,
            image_height=frame_height,
            inference_ms=round(inference_ms, 2),
            detections=detections,
        )
