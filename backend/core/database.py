"""
SQLAlchemy async-compatible database setup (SQLite for local-first operation).
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.core.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # needed for SQLite
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency — yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables on startup."""
    # Import models so SQLAlchemy registers them before create_all
    import backend.models.agent  # noqa: F401
    import backend.models.workflow  # noqa: F401
    import backend.models.execution  # noqa: F401

    Base.metadata.create_all(bind=engine)
