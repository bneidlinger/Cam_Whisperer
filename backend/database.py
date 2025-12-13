# backend/database.py
"""
Database setup and session management for PlatoniCam.
Uses SQLAlchemy 2.0 with async support.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from contextlib import contextmanager
from typing import Generator

from config import settings


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# Create engine with SQLite-specific settings
# For SQLite, we need check_same_thread=False for FastAPI's async context
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=settings.app_env == "development",  # Log SQL in development
    pool_pre_ping=True,  # Verify connections before using
)

# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


def init_db() -> None:
    """
    Initialize the database by creating all tables.
    Called on application startup.
    """
    # Import all models to ensure they're registered with Base
    from models import orm  # noqa: F401

    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db_session() -> Generator:
    """
    Context manager for database sessions.
    Ensures proper cleanup on exceptions.

    Usage:
        with get_db_session() as db:
            db.query(Model).all()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator:
    """
    Dependency for FastAPI endpoints.
    Yields a database session and cleans up after request.

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
