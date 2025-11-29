"""Shared test fixtures for all tests."""

import asyncio
import os
from typing import AsyncGenerator
from datetime import datetime, UTC

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text as sa_text
from sqlmodel import SQLModel

from app.models.user import User
from app.models.email import EmailProcessingQueue
from app.models.workflow_mapping import WorkflowMapping
from app.models.folder_category import FolderCategory
from app.models.notification_preferences import NotificationPreferences
from app.models.approval_history import ApprovalHistory
from app.models.indexing_progress import IndexingProgress
from app.models.linking_codes import LinkingCode
from app.models.prompt_versions import PromptVersion
from app.models.session import Session
from app.models.thread import Thread

# Import LazyAsyncSession using relative path
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from utils.lazy_async_session import LazyAsyncSession

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://mailagent:mailagent_dev_password_2024@localhost:5432/mailagent")

# Global engine for sharing between db_session and workflow_db_session
_test_engine = None


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test.

    This fixture creates tables, yields a session, then drops all tables
    after the test completes to ensure isolation between tests.

    For workflow tests that need cross-context session support, use the
    `workflow_db_session` fixture instead.
    """
    global _test_engine

    # Create async engine for test database
    _test_engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=3600,  # Recycle connections after 1 hour
    )

    # Clean up any existing tables first (in case previous test cleanup failed)
    async with _test_engine.begin() as conn:
        await conn.execute(sa_text("DROP TABLE IF EXISTS prompt_versions CASCADE"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS linking_codes CASCADE"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS indexing_progress CASCADE"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS approval_history CASCADE"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS workflow_mappings CASCADE"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS email_processing_queue CASCADE"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS notification_preferences CASCADE"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS folder_categories CASCADE"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS session CASCADE"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS thread CASCADE"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS users CASCADE"))

    # Create tables needed for tests
    # Note: EmailProcessingQueue has FK to folder_categories, so we must create it too
    # folder_categories uses ARRAY type which REQUIRES PostgreSQL (not SQLite)
    async with _test_engine.begin() as conn:
        # Create tables in dependency order (parent tables first)
        await conn.run_sync(User.__table__.create, checkfirst=True)
        await conn.run_sync(Thread.__table__.create, checkfirst=True)  # Chat threads (no FK dependencies)
        await conn.run_sync(Session.__table__.create, checkfirst=True)  # Chat sessions (FK to users)
        await conn.run_sync(FolderCategory.__table__.create, checkfirst=True)  # Required by EmailProcessingQueue FK
        await conn.run_sync(NotificationPreferences.__table__.create, checkfirst=True)
        await conn.run_sync(EmailProcessingQueue.__table__.create, checkfirst=True)
        await conn.run_sync(WorkflowMapping.__table__.create, checkfirst=True)
        await conn.run_sync(ApprovalHistory.__table__.create, checkfirst=True)
        await conn.run_sync(IndexingProgress.__table__.create, checkfirst=True)  # Epic 3 email indexing progress
        await conn.run_sync(LinkingCode.__table__.create, checkfirst=True)  # Telegram linking codes
        await conn.run_sync(PromptVersion.__table__.create, checkfirst=True)  # Prompt versioning

    # Create session
    async_session = async_sessionmaker(
        _test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        # Ensure any uncommitted changes are rolled back before cleanup
        await session.rollback()
        await session.close()

    # Drop tables with CASCADE to handle foreign key constraints from other tables
    async with _test_engine.begin() as conn:
        # Use raw SQL with CASCADE to drop tables cleanly (reverse order of creation)
        await conn.execute(sa_text("DROP TABLE IF EXISTS prompt_versions CASCADE"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS linking_codes CASCADE"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS indexing_progress CASCADE"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS approval_history CASCADE"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS workflow_mappings CASCADE"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS email_processing_queue CASCADE"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS notification_preferences CASCADE"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS folder_categories CASCADE"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS session CASCADE"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS thread CASCADE"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS users CASCADE"))

    await _test_engine.dispose()
    _test_engine = None


@pytest_asyncio.fixture(scope="function")
async def workflow_db_session_factory(db_session: AsyncSession):
    """Create an AsyncSession factory for workflow tests.

    This fixture provides a session factory that creates fresh sessions for each
    database operation within workflow nodes. This follows SQLAlchemy + LangGraph
    best practices for cross-context async operations.

    Usage:
        Use `db_session` for test setup and verification.
        Use `workflow_db_session_factory` for passing to create_email_workflow().

    Args:
        db_session: The regular db_session fixture (ensures engine is created)

    Yields:
        async_sessionmaker factory that creates AsyncSession instances
    """
    global _test_engine

    if _test_engine is None:
        raise RuntimeError("db_session fixture must be used before workflow_db_session_factory")

    # CRITICAL: Verify that _test_engine is actually an AsyncEngine
    # This prevents the "AsyncEngine expected, got Engine" error
    from sqlalchemy.ext.asyncio import AsyncEngine
    from sqlalchemy.engine import Engine
    if isinstance(_test_engine, Engine) and not isinstance(_test_engine, AsyncEngine):
        raise TypeError(
            f"FATAL: _test_engine is a sync Engine instead of AsyncEngine! "
            f"Type: {type(_test_engine)}, URL: {_test_engine.url}"
        )

    session_factory = async_sessionmaker(
        _test_engine, class_=AsyncSession, expire_on_commit=False
    )

    yield session_factory


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user with Telegram linked."""
    user = User(
        email="test@example.com",
        is_active=True,
        telegram_id="123456789",
        telegram_username="testuser",
        telegram_linked_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_user_2(db_session: AsyncSession) -> User:
    """Create a second test user with different Telegram ID."""
    user = User(
        email="test2@example.com",
        is_active=True,
        telegram_id="987654321",
        telegram_username="testuser2",
        telegram_linked_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_email(db_session: AsyncSession, test_user: User) -> EmailProcessingQueue:
    """Create a test email in processing queue."""
    email = EmailProcessingQueue(
        user_id=test_user.id,
        gmail_message_id="test-gmail-msg-123",
        gmail_thread_id="test-thread-456",
        sender="sender@example.com",
        recipient="test@example.com",
        subject="Test Email Subject",
        body_plain="This is a test email body for unit testing.",
        received_at=datetime.now(UTC),
        processing_status="pending",
        created_at=datetime.now(UTC),
    )
    db_session.add(email)
    await db_session.commit()
    await db_session.refresh(email)
    return email


@pytest_asyncio.fixture
async def test_folder(db_session: AsyncSession, test_user: User) -> FolderCategory:
    """Create a test folder category."""
    folder = FolderCategory(
        user_id=test_user.id,
        name="Government",
        gmail_label_id="Label_Government",
        keywords=["tax", "gov", "official"],
        priority_domains=[],
        is_system_folder=False,
        created_at=datetime.now(UTC),
    )
    db_session.add(folder)
    await db_session.commit()
    await db_session.refresh(folder)
    return folder


@pytest_asyncio.fixture
async def test_notification_prefs(db_session: AsyncSession, test_user: User) -> NotificationPreferences:
    """Create test notification preferences for user."""
    from datetime import time as dt_time
    prefs = NotificationPreferences(
        user_id=test_user.id,
        batch_enabled=True,
        batch_time=dt_time(18, 0),
        priority_immediate=True,
        quiet_hours_start=None,
        quiet_hours_end=None,
        timezone="UTC",
    )
    db_session.add(prefs)
    await db_session.commit()
    await db_session.refresh(prefs)
    return prefs


@pytest_asyncio.fixture(autouse=True)
async def cleanup_langgraph_checkpoints(db_session: AsyncSession):
    """Clean up LangGraph checkpoints table between tests.

    This fixture ensures isolated workflow execution by clearing all
    checkpoints before and after each test. It's marked autouse=True
    so it runs automatically for all tests without explicit declaration.
    """
    # Clean before test
    try:
        await db_session.execute(sa_text("TRUNCATE TABLE checkpoints CASCADE"))
        await db_session.commit()
    except Exception:
        # Table might not exist yet (first run), that's okay
        await db_session.rollback()

    yield

    # Clean after test
    try:
        await db_session.execute(sa_text("TRUNCATE TABLE checkpoints CASCADE"))
        await db_session.commit()
    except Exception:
        # Table might have been dropped, that's okay
        await db_session.rollback()


# ========================================
# Mock Service Fixtures for DI
# ========================================

@pytest.fixture
def mock_embedding_service():
    """Mock EmbeddingService for tests requiring dependency injection."""
    from unittest.mock import Mock
    mock_service = Mock()
    mock_service.embed_text.return_value = [0.15] * 768  # Consistent embedding
    return mock_service


@pytest.fixture
def mock_vector_db_client():
    """Mock VectorDBClient for tests requiring dependency injection."""
    from unittest.mock import AsyncMock
    mock_client = AsyncMock()
    # Mock semantic search to return empty results by default
    mock_client.search_similar_emails.return_value = []
    return mock_client


@pytest.fixture
def mock_context_service():
    """Mock ContextRetrievalService for tests requiring dependency injection."""
    from unittest.mock import AsyncMock

    mock_service = AsyncMock()
    # Return minimal context by default with proper metadata structure
    mock_service.retrieve_context.return_value = {
        "thread_history": [],
        "semantic_results": [],
        "metadata": {
            "thread_length": 0,
            "semantic_count": 0,
            "total_tokens_used": 0
        }
    }
    return mock_service
