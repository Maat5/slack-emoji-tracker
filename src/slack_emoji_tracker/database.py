"""Database management and connection utilities."""

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from .config import config
from .models import Base

logger = logging.getLogger(__name__)

# Create the database engine
engine = create_engine(
    config.database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=config.environment == "development",
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables() -> None:
    """Create all tables in the database."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except SQLAlchemyError as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def check_database_connection() -> bool:
    """Check if the database connection is working."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError as e:
        logger.error(f"Database connection failed: {e}")
        return False


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Get a database session with proper cleanup."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI to get database sessions."""
    with get_db_session() as session:
        yield session