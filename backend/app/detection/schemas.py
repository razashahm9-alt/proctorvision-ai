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
    detections: list[DetectionItem]


class ModelStatusResponse(BaseModel):
    loaded: bool
    model_path: str
    model_file_exists: bool
    required_classes: list[str]
