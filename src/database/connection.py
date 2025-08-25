"""Database connection management."""

import logging
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.models.database import Base
from src.utils.config import config

logger = logging.getLogger(__name__)

# Create database engine
engine = create_engine(
    config.database_url,
    echo=config.debug,  # Log SQL queries in debug mode
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=300,    # Recycle connections every 5 minutes
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables() -> None:
    """Create all database tables."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def get_db() -> Generator[Session, None, None]:
    """
    Get database session.
    
    This function is designed to be used as a dependency in FastAPI.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class DatabaseManager:
    """Database manager for handling database operations."""

    def __init__(self) -> None:
        """Initialize the database manager."""
        self.engine = engine
        self.SessionLocal = SessionLocal

    def create_tables(self) -> None:
        """Create all database tables."""
        create_tables()

    def get_session(self) -> Session:
        """Get a new database session."""
        return SessionLocal()

    def close_session(self, session: Session) -> None:
        """Close a database session."""
        session.close()

    def test_connection(self) -> bool:
        """Test the database connection."""
        try:
            with self.engine.connect() as connection:
                connection.execute("SELECT 1")
            logger.info("Database connection successful")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False


# Global database manager instance
db_manager = DatabaseManager()