"""API schemas returned by the device detector."""

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int


class DetectionItem(BaseModel):
    class_name: str
    display_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    box: BoundingBox


class FrameDetectionResponse(BaseModel):
    detected: bool
    device_count: int
    image_width: int
    image_height: int
    inference_ms: float
    runtime: str = "CPU"
    model_name: str = "YOLO"
    detections: list[DetectionItem]


class ModelStatusResponse(BaseModel):
    loaded: bool
    model_path: str
    model_file_exists: bool
    runtime: str
    model_name: str
    using_fallback: bool
    preferred_model_path: str
    warmup_ms: float | None
    required_classes: list[str]
