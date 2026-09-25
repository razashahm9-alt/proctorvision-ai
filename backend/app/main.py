"""FastAPI entry point for ProctorVision AI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .api.detection import get_detector, router as detection_router
from .core.config import settings


class HealthResponse(BaseModel):
    status: str
    application: str
    version: str
    detector: str


app = FastAPI(
    title="ProctorVision AI API",
    description="Backend API for real-time prohibited-device monitoring.",
    version=settings.app_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(detection_router, prefix="/api")


@app.get("/", tags=["System"])
def root() -> dict[str, str]:
    return {
        "application": "ProctorVision AI API",
        "message": "Backend is running. Open /docs for interactive API documentation.",
    }


@app.get("/api/health", response_model=HealthResponse, tags=["System"])
def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        application=settings.app_name,
        version=settings.app_version,
        detector="loaded" if get_detector().loaded else "not_loaded",
    )
