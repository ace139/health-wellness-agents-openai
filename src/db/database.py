"""Database connection and session management."""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import settings
from .models import Base

# Create SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DB_DRIVER == "sqlite" else {},
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency that provides a database session.

    Yields:
        Session: A database session

    Example:
        ```python
        def some_endpoint(db: Session = Depends(get_db)):
            # Use the database session
            users = db.query(User).all()
            return users
        ```
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize the database by creating all tables."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Context manager for database sessions.

    Example:
        ```python
        with get_db_context() as db:
            # Use the database session
            users = db.query(User).all()
        ```
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """Get a new database session.

    Returns:
        Session: A database session

    Note:
        Remember to close the session when done using `session.close()`
    """
    return SessionLocal()
