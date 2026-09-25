"""HTTP endpoints for model status and single-frame detection."""

import cv2
import numpy as np
from fastapi import APIRouter, File, HTTPException, UploadFile, status

from ..core.config import settings
from ..detection.detector import DeviceDetector
from ..detection.schemas import FrameDetectionResponse, ModelStatusResponse


router = APIRouter(prefix="/detection", tags=["Detection"])
detector = DeviceDetector(settings)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAXIMUM_IMAGE_BYTES = 10 * 1024 * 1024


def get_detector() -> DeviceDetector:
    return detector


@router.get("/model", response_model=ModelStatusResponse)
def model_status() -> ModelStatusResponse:
    """Return model availability without loading model weights."""

    return ModelStatusResponse(**detector.status())


@router.post("/model/load", response_model=ModelStatusResponse)
def load_model() -> ModelStatusResponse:
    """Load and validate YOLO model weights on demand."""

    try:
        detector.load()
    except (FileNotFoundError, RuntimeError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

    return ModelStatusResponse(**detector.status())


@router.post("/frame", response_model=FrameDetectionResponse)
async def detect_frame(image: UploadFile = File(...)) -> FrameDetectionResponse:
    """Detect prohibited devices in one uploaded image frame."""

    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload a JPEG, PNG, or WebP image.",
        )

    payload = await image.read(MAXIMUM_IMAGE_BYTES + 1)
    if len(payload) > MAXIMUM_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image exceeds the 10 MB upload limit.",
        )

    encoded = np.frombuffer(payload, dtype=np.uint8)
    frame = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is not a valid image.",
        )

    try:
        return detector.detect(frame)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    finally:
        await image.close()
