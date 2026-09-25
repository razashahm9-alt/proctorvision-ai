"""FastAPI entry point for ProctorVision AI."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .api.detection import get_detector, router as detection_router
from .core.config import settings
from .database import init_db


class HealthResponse(BaseModel):
    status: str
    application: str
    version: str
    detector: str


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Initialize persistent resources when FastAPI starts."""

    init_db()
    yield


app = FastAPI(
    title="ProctorVision AI API",
    description="Backend API for real-time prohibited-device monitoring.",
    version=settings.app_version,
    lifespan=lifespan,
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
