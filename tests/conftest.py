from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.models import Base
from src.tasks.celery_app import app as celery_app
from src.tasks.send_email import send_email

# ---------------------------------------------------------------------------
# Database Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_engine():
    """Create an in-memory SQLite engine once per test session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(test_engine):
    """
    Provide an isolated database session per test.
    Rolls back all DB operations after the test completes.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# Celery & Task Mocks
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_celery_app():
    """Mock Celery application and its configuration."""
    with patch("src.tasks.send_email.app") as mock_app:
        mock_app.conf = celery_app.conf
        mock_app.AsyncResult = MagicMock()
        yield mock_app


@pytest.fixture
def send_email_task(db_session):
    """
    Yield the send_email task with mock dependencies (DB, Logger, Timestamps).
    """
    # Patch SessionLocal to return our isolated test db_session
    with patch("src.tasks.send_email.SessionLocal", return_value=db_session), \
         patch("src.tasks.send_email.logger") as mock_logger, \
         patch("src.tasks.send_email.func.now", return_value="2025-01-01T00:00:00") as mock_now:
        
        yield send_email