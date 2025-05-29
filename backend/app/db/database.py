"""Database engine and session management."""

import logging
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import get_settings

logger = logging.getLogger(__name__)

# Global engine instance
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the global database engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        # Connection pooling strategy selection based on environment
        # Option 1: NullPool - Creates and closes connections for each request
        # Pros: No connection limit issues, works well in containerized environments
        # Cons: Slightly higher latency due to connection overhead
        _engine = create_engine(
            settings.get_active_database_url(),
            poolclass=NullPool,
            echo=False,
        )

        # Option 2: QueuePool with conservative settings (uncomment to use)
        # Pros: Better performance with connection reuse
        # Cons: Must carefully manage pool size to avoid exhaustion
        # _engine = create_engine(
        #     settings.get_active_database_url(),
        #     poolclass=QueuePool,
        #     pool_size=5,  # Number of persistent connections
        #     max_overflow=5,  # Maximum overflow connections
        #     pool_timeout=30,  # Timeout waiting for connection
        #     pool_recycle=1800,  # Recycle connections after 30 minutes
        #     pool_pre_ping=True,  # Test connections before use
        #     echo=False,
        # )
        logger.info("Created database engine with NullPool")
    return _engine


def get_session_factory():
    """Get or create the global session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=get_engine()
        )
        logger.info("Created session factory")
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a database session.
    Ensures proper cleanup after use.
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
