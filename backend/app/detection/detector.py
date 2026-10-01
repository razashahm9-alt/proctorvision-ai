"""Reusable YOLO service for prohibited-device detection."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
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
        self._active_model_path: Path | None = None
        self._runtime = ""
        self._warmup_ms: float | None = None
        self._load_lock = threading.Lock()
        self._inference_lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._model is not None

    @property
    def model_path(self) -> Path:
        return self._active_model_path or self.settings.selected_model_path

    @property
    def runtime(self) -> str:
        return self._runtime or self.settings.selected_model_runtime

    @property
    def model_name(self) -> str:
        name = self.model_path.stem if self.model_path.suffix else self.model_path.name
        return name.removesuffix("_openvino_model")

    def status(self) -> dict[str, object]:
        model_path = self.model_path
        return {
            "loaded": self.loaded,
            "model_path": str(model_path),
            "model_file_exists": model_path.exists(),
            "runtime": self.runtime,
            "model_name": self.model_name,
            "using_fallback": (
                self.settings.prefer_openvino
                and model_path != self.settings.openvino_model_path
            ),
            "preferred_model_path": str(self.settings.openvino_model_path),
            "warmup_ms": self._warmup_ms,
            "required_classes": list(DISPLAY_NAMES.values()),
        }

    def _predict(
        self,
        model: Any,
        frame: np.ndarray,
        runtime: str,
        target_ids: dict[int, str] | None = None,
    ) -> list[Any]:
        """Run a prediction with runtime-appropriate arguments."""

        selected_target_ids = target_ids or self._target_ids
        arguments = {
            "source": frame,
            "imgsz": self.settings.image_size,
            "conf": self.settings.raw_confidence,
            "iou": self.settings.iou_threshold,
            "classes": list(selected_target_ids),
            "max_det": self.settings.maximum_detections,
            "verbose": False,
        }
        if runtime == "PyTorch CPU":
            arguments["device"] = self.settings.device
        return model.predict(**arguments)

    def _initialize_candidate(
        self,
        model_path: Path,
        runtime: str,
    ) -> tuple[Any, dict[int, str], float | None]:
        """Load, validate, and optionally warm one runtime candidate."""

        model = YOLO(str(model_path))
        target_ids = {
            int(class_id): class_name
            for class_id, class_name in model.names.items()
            if class_name in DISPLAY_NAMES
        }
        missing_classes = set(DISPLAY_NAMES) - set(target_ids.values())
        if missing_classes:
            missing = ", ".join(sorted(missing_classes))
            raise RuntimeError(f"Model is missing required classes: {missing}")

        warmup_ms = None
        if self.settings.warmup_model:
            warmup_frame = np.zeros(
                (self.settings.image_size, self.settings.image_size, 3),
                dtype=np.uint8,
            )
            started = time.perf_counter()
            self._predict(
                model,
                warmup_frame,
                runtime,
                target_ids,
            )
            warmup_ms = round((time.perf_counter() - started) * 1000, 2)

        return model, target_ids, warmup_ms

    def load(self) -> None:
        """Load and validate the configured model exactly once."""

        if self.loaded:
            return

        with self._load_lock:
            if self.loaded:
                return

            selected_path = self.settings.selected_model_path
            candidates = [
                (selected_path, self.settings.selected_model_runtime),
            ]
            if selected_path == self.settings.openvino_model_path:
                candidates.append((self.settings.model_path, "PyTorch CPU"))

            failures: list[str] = []
            for model_path, runtime in candidates:
                if not model_path.exists():
                    failures.append(f"model not found: {model_path}")
                    continue
                try:
                    model, target_ids, warmup_ms = self._initialize_candidate(
                        model_path,
                        runtime,
                    )
                except (ImportError, OSError, RuntimeError, ValueError) as error:
                    failures.append(f"{runtime}: {error}")
                    continue

                self._model = model
                self._target_ids = target_ids
                self._active_model_path = model_path
                self._runtime = runtime
                self._warmup_ms = warmup_ms
                return

            details = "; ".join(failures)
            raise RuntimeError(f"Unable to initialize YOLO. {details}")

    def detect(self, frame: np.ndarray) -> FrameDetectionResponse:
        """Run inference on one decoded BGR image frame."""

        if frame.size == 0:
            raise ValueError("The supplied image frame is empty.")

        self.load()
        frame_height, frame_width = frame.shape[:2]

        started = time.perf_counter()
        with self._inference_lock:
            results = self._predict(self._model, frame, self.runtime)
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
            runtime=self.runtime,
            model_name=self.model_name,
            detections=detections,
        )
