"""SQLAlchemy engine, sessions, and table initialization."""

from collections.abc import Generator
from sqlite3 import Connection as SQLiteConnection

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from ..core.config import settings


class Base(DeclarativeBase):
    """Base class for all ProctorVision database models."""


settings.database_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    """Enable SQLite foreign-key enforcement for every SQLite connection."""

    if isinstance(dbapi_connection, SQLiteConnection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def init_db() -> None:
    """Create all configured tables without deleting existing data."""

    from . import models  # noqa: F401 - imports model metadata before create_all

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Provide a database session for future FastAPI dependencies."""

    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()
