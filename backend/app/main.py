"""Initial FastAPI entry point for ProctorVision AI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


APP_VERSION = "0.1.0"


class HealthResponse(BaseModel):
    """Response returned by the backend health endpoint."""

    status: str
    application: str
    version: str
    detector: str


app = FastAPI(
    title="ProctorVision AI API",
    description="Backend API for real-time prohibited-device monitoring.",
    version=APP_VERSION,
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


@app.get("/", tags=["System"])
def root() -> dict[str, str]:
    """Provide a small landing response for the API root."""

    return {
        "application": "ProctorVision AI API",
        "message": "Backend is running. Open /docs for interactive API documentation.",
    }


@app.get("/api/health", response_model=HealthResponse, tags=["System"])
def health_check() -> HealthResponse:
    """Report whether the initial backend service is available."""

    return HealthResponse(
        status="healthy",
        application="ProctorVision AI",
        version=APP_VERSION,
        detector="not_loaded",
    )
