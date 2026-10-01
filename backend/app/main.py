"""FastAPI entry point for ProctorVision AI."""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import text
from starlette.concurrency import run_in_threadpool

from .api.auth import router as auth_router
from .api.detection import get_detector, router as detection_router
from .api.history import router as history_router
from .api.monitoring import router as monitoring_router
from .core.config import settings
from .core.security import access_cookie_is_valid
from .database import init_db
from .database.base import SessionLocal


logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: str
    application: str
    version: str
    detector: str
    runtime: str
    model: str
    access_protected: bool
    frontend: str


class ReadinessResponse(BaseModel):
    ready: bool
    database: str
    detector: str
    runtime: str


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Initialize persistent resources when FastAPI starts."""

    init_db()
    if settings.preload_model:
        try:
            detector = get_detector()
            await run_in_threadpool(detector.load)
            detector_status = detector.status()
            logger.info(
                "Detector ready: %s via %s (warm-up %s ms)",
                detector_status["model_name"],
                detector_status["runtime"],
                detector_status["warmup_ms"],
            )
            if detector_status["using_fallback"]:
                logger.warning(
                    "OpenVINO export not found; using the PyTorch CPU fallback."
                )
        except (FileNotFoundError, ImportError, RuntimeError, OSError) as error:
            logger.warning("Detector preload failed: %s", error)
    yield


app = FastAPI(
    title="ProctorVision AI API",
    description="Backend API for real-time prohibited-device monitoring.",
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PUBLIC_API_PATHS = {
    "/api/health",
    "/api/ready",
    "/api/auth/status",
    "/api/auth/login",
    "/api/auth/logout",
}


@app.middleware("http")
async def deployment_security(request: Request, call_next):
    """Protect audit APIs when configured and add conservative headers."""

    path = request.url.path.rstrip("/") or "/"
    protected_api = (path == "/api" or path.startswith("/api/")) and (
        path not in PUBLIC_API_PATHS
    )
    protected_documentation = path in {"/docs", "/redoc", "/openapi.json"}
    authorized = access_cookie_is_valid(
        request.cookies.get(settings.access_cookie_name)
    )

    if (
        settings.access_protection_enabled
        and (protected_api or protected_documentation)
        and not authorized
    ):
        response = JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Supervisor access is required."},
        )
    else:
        response = await call_next(request)

    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(self), microphone=(), geolocation=()",
    )
    return response


app.include_router(auth_router, prefix="/api")
app.include_router(detection_router, prefix="/api")
app.include_router(monitoring_router, prefix="/api")
app.include_router(history_router, prefix="/api")


@app.get("/api", tags=["System"])
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
        runtime=get_detector().runtime,
        model=get_detector().model_name,
        access_protected=settings.access_protection_enabled,
        frontend="available" if settings.frontend_available else "not_built",
    )


@app.get("/api/ready", response_model=ReadinessResponse, tags=["System"])
def readiness_check() -> JSONResponse | ReadinessResponse:
    """Report whether persistent storage and the detector are ready for use."""

    database_status = "ready"
    try:
        with SessionLocal() as database:
            database.execute(text("SELECT 1"))
    except Exception:  # pragma: no cover - depends on host filesystem/runtime
        logger.exception("Database readiness check failed.")
        database_status = "unavailable"

    detector = get_detector()
    ready = database_status == "ready" and detector.loaded
    payload = ReadinessResponse(
        ready=ready,
        database=database_status,
        detector="loaded" if detector.loaded else "not_loaded",
        runtime=detector.runtime,
    )
    if ready:
        return payload
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=payload.model_dump(),
    )


if settings.frontend_available:
    app.mount(
        "/",
        StaticFiles(directory=settings.frontend_dist_directory, html=True),
        name="frontend",
    )
else:

    @app.get("/", tags=["System"], include_in_schema=False)
    def development_root() -> dict[str, str]:
        return root()
