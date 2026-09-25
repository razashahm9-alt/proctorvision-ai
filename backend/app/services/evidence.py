"""Save annotated evidence frames for confirmed device incidents."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from ..detection.schemas import DetectionItem


DEVICE_COLORS = {
    "cell phone": (0, 215, 255),
    "laptop": (255, 180, 0),
    "tv": (180, 0, 255),
}


class EvidenceWriter:
    """Write one annotated JPEG when an incident is first confirmed."""

    def __init__(self, evidence_directory: Path) -> None:
        self.evidence_directory = Path(evidence_directory)

    def save(
        self,
        *,
        frame: np.ndarray,
        session_id: str,
        incident_id: str,
        device_key: str,
        detections: list[DetectionItem],
    ) -> str:
        if frame.size == 0:
            raise ValueError("Cannot save an empty evidence frame.")

        session_directory = self.evidence_directory / session_id
        session_directory.mkdir(parents=True, exist_ok=True)
        output_path = session_directory / f"{incident_id}.jpg"

        annotated = frame.copy()
        color = DEVICE_COLORS.get(device_key, (0, 215, 255))
        for detection in detections:
            if detection.class_name != device_key:
                continue
            box = detection.box
            cv2.rectangle(
                annotated,
                (box.x1, box.y1),
                (box.x2, box.y2),
                color,
                2,
            )
            label = f"{detection.display_name} {detection.confidence:.0%}"
            label_y = max(22, box.y1 - 8)
            cv2.putText(
                annotated,
                label,
                (box.x1, label_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2,
                cv2.LINE_AA,
            )

        if not cv2.imwrite(str(output_path), annotated):
            raise OSError(f"Could not save evidence image: {output_path}")

        return str(output_path)
