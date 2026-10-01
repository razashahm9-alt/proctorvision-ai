"""Central configuration for the ProctorVision AI backend."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Environment-aware application settings."""

    app_name: str = "ProctorVision AI"
    app_version: str = "0.8.1"
    environment: str = "development"
    model_path: Path = PROJECT_ROOT / "yolo11s.pt"
    openvino_model_path: Path = PROJECT_ROOT / "yolo11s_openvino_model"
    prefer_openvino: bool = True
    preload_model: bool = True
    warmup_model: bool = True
    database_path: Path = PROJECT_ROOT / "data" / "proctorvision.db"
    evidence_directory: Path = PROJECT_ROOT / "evidence"
    frontend_dist_directory: Path = PROJECT_ROOT / "frontend" / "dist"
    serve_frontend: bool = True
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    access_token: str = ""
    access_cookie_name: str = "proctorvision_access"
    access_session_hours: int = 8
    secure_cookies: bool = False
    image_size: int = 416
    raw_confidence: float = 0.25
    iou_threshold: float = 0.50
    device: str = "cpu"
    maximum_detections: int = 10
    confirmation_window_frames: int = 5
    confirmation_required_frames: int = 3
    instant_confirmation_confidence: float = 0.80
    fast_confirmation_confidence: float = 0.55
    fast_confirmation_window_frames: int = 3
    fast_confirmation_required_frames: int = 2
    incident_clear_delay_seconds: float = 2.0
    maximum_websocket_frame_bytes: int = 3 * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_prefix="PROCTORVISION_",
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        """Return a Windows-safe SQLAlchemy URL for the SQLite database."""

        return f"sqlite:///{self.database_path.as_posix()}"

    @property
    def cors_origin_list(self) -> list[str]:
        """Return normalized origins configured for cross-origin development."""

        return [
            origin.strip().rstrip("/")
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def access_protection_enabled(self) -> bool:
        """Enable the lightweight supervisor gate only when a token is set."""

        return bool(self.access_token.strip())

    @property
    def frontend_available(self) -> bool:
        """Return whether a production Vite build can be served by FastAPI."""

        return (
            self.serve_frontend
            and self.frontend_dist_directory.is_dir()
            and (self.frontend_dist_directory / "index.html").is_file()
        )

    @property
    def selected_model_path(self) -> Path:
        """Prefer an exported OpenVINO model and safely fall back to PyTorch."""

        if self.prefer_openvino and self.openvino_model_available:
            return self.openvino_model_path
        return self.model_path

    @property
    def openvino_model_available(self) -> bool:
        """Require both OpenVINO graph files before selecting an export."""

        path = self.openvino_model_path
        if path.is_file():
            return path.suffix.lower() == ".xml"
        if not path.is_dir():
            return False
        return any(path.glob("*.xml")) and any(path.glob("*.bin"))

    @property
    def selected_model_runtime(self) -> str:
        """Describe the runtime selected from the configured model path."""

        path = self.selected_model_path
        normalized_name = path.name.lower()
        if path.is_dir() or "openvino" in normalized_name or path.suffix == ".xml":
            return "OpenVINO CPU"
        return "PyTorch CPU"


settings = Settings()
