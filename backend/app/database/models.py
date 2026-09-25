"""Database tables for monitoring sessions and violation incidents."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


def utc_now() -> datetime:
    """Return naive UTC for consistent SQLite storage."""

    return datetime.now(UTC).replace(tzinfo=None)


class MonitoringSession(Base):
    __tablename__ = "monitoring_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="Active", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_incidents: Mapped[int] = mapped_column(Integer, default=0)

    incidents: Mapped[list[Incident]] = relationship(
        back_populates="monitoring_session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("monitoring_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    device_key: Mapped[str] = mapped_column(String(30), index=True)
    device_name: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(20), default="Active", index=True)
    maximum_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    maximum_count: Mapped[int] = mapped_column(Integer, default=1)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_path: Mapped[str] = mapped_column(Text, default="")

    monitoring_session: Mapped[MonitoringSession] = relationship(
        back_populates="incidents"
    )
