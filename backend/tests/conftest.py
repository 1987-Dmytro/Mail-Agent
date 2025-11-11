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

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://mailagent:mailagent_dev_password_2024@localhost:5432/mailagent")


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
    """
    # Create async engine for test database
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
    )

    # Create tables needed for tests
    # Note: EmailProcessingQueue has FK to folder_categories, so we must create it too
    # folder_categories uses ARRAY type which REQUIRES PostgreSQL (not SQLite)
    async with engine.begin() as conn:
        # Create tables in dependency order (parent tables first)
        await conn.run_sync(User.__table__.create, checkfirst=True)
        await conn.run_sync(FolderCategory.__table__.create, checkfirst=True)  # Required by EmailProcessingQueue FK
        await conn.run_sync(NotificationPreferences.__table__.create, checkfirst=True)
        await conn.run_sync(EmailProcessingQueue.__table__.create, checkfirst=True)
        await conn.run_sync(WorkflowMapping.__table__.create, checkfirst=True)
        await conn.run_sync(ApprovalHistory.__table__.create, checkfirst=True)
        await conn.run_sync(IndexingProgress.__table__.create, checkfirst=True)  # Epic 3 email indexing progress

    # Create session
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    # Drop tables with CASCADE to handle foreign key constraints from other tables
    async with engine.begin() as conn:
        # Use raw SQL with CASCADE to drop tables cleanly
        await conn.execute(sa_text("DROP TABLE IF EXISTS indexing_progress CASCADE"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS approval_history CASCADE"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS workflow_mappings CASCADE"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS email_processing_queue CASCADE"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS notification_preferences CASCADE"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS folder_categories CASCADE"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS users CASCADE"))

    await engine.dispose()


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
