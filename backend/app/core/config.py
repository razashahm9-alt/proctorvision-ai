"""Central configuration for the ProctorVision AI backend."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Environment-aware application settings."""

    app_name: str = "ProctorVision AI"
    app_version: str = "0.3.0"
    model_path: Path = PROJECT_ROOT / "yolo11s.pt"
    database_path: Path = PROJECT_ROOT / "data" / "proctorvision.db"
    evidence_directory: Path = PROJECT_ROOT / "evidence"
    image_size: int = 416
    raw_confidence: float = 0.25
    iou_threshold: float = 0.50
    device: str = "cpu"
    maximum_detections: int = 10

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_prefix="PROCTORVISION_",
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        """Return a Windows-safe SQLAlchemy URL for the SQLite database."""

        return f"sqlite:///{self.database_path.as_posix()}"


settings = Settings()
