from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import settings
from src.db.models import Base
from src.utils.logger import logger

# Normalize legacy postgres:// scheme if provided
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# Configure engine with dialect-specific connection pool settings
engine_kwargs = {"pool_pre_ping": True}
if "postgresql" in db_url:
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
    })
elif "sqlite" in db_url:
    engine_kwargs.update({
        "connect_args": {"check_same_thread": False}
    })

engine = create_engine(db_url, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all database tables on application initialization."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("database_tables_initialized")
    except Exception as e:
        logger.error("database_init_failed", error=str(e))
        raise


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for obtaining a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Context manager for obtaining a database session outside HTTP requests."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
