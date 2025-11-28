"""Unit tests for EmailProcessingQueue model."""

from datetime import datetime, UTC

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.models.email import EmailProcessingQueue
from app.models.user import User


@pytest.mark.asyncio
async def test_email_model_creation(db_session):
    """Test creating EmailProcessingQueue record with all required fields."""
    # Create test user
    user = User(email="test@example.com", is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create email record
    email = EmailProcessingQueue(
        user_id=user.id,
        gmail_message_id="test_message_123",
        gmail_thread_id="test_thread_456",
        sender="sender@example.com",
        subject="Test Subject",
        received_at=datetime.now(UTC),
        status="pending",
    )
    db_session.add(email)
    await db_session.commit()
    await db_session.refresh(email)

    # Verify all fields
    assert email.id is not None
    assert email.user_id == user.id
    assert email.gmail_message_id == "test_message_123"
    assert email.gmail_thread_id == "test_thread_456"
    assert email.sender == "sender@example.com"
    assert email.subject == "Test Subject"
    assert email.status == "pending"
    assert email.received_at is not None
    assert email.created_at is not None
    assert email.updated_at is not None


@pytest.mark.asyncio
async def test_email_user_relationship(db_session):
    """Test relationship between EmailProcessingQueue and User models."""
    # Create user
    user = User(email="test@example.com", is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create multiple emails for user
    email1 = EmailProcessingQueue(
        user_id=user.id,
        gmail_message_id="msg_001",
        gmail_thread_id="thread_001",
        sender="sender1@example.com",
        subject="Email 1",
        received_at=datetime.now(UTC),
        status="pending",
    )
    email2 = EmailProcessingQueue(
        user_id=user.id,
        gmail_message_id="msg_002",
        gmail_thread_id="thread_001",
        sender="sender2@example.com",
        subject="Email 2",
        received_at=datetime.now(UTC),
        status="processing",
    )
    db_session.add(email1)
    db_session.add(email2)
    await db_session.commit()

    # Refresh user to load relationship
    await db_session.refresh(user)

    # Verify relationship traversal (User -> Emails)
    statement = select(User).where(User.id == user.id)
    result = await db_session.execute(statement)
    fetched_user = result.scalar_one()

    # Load relationship explicitly if needed
    statement = select(EmailProcessingQueue).where(EmailProcessingQueue.user_id == user.id)
    result = await db_session.execute(statement)
    user_emails = result.scalars().all()

    assert len(user_emails) == 2
    assert {e.gmail_message_id for e in user_emails} == {"msg_001", "msg_002"}

    # Verify relationship traversal (Email -> User)
    await db_session.refresh(email1)
    statement = select(EmailProcessingQueue).where(EmailProcessingQueue.id == email1.id)
    result = await db_session.execute(statement)
    fetched_email = result.scalar_one()
    assert fetched_email.user_id == user.id


@pytest.mark.asyncio
async def test_unique_gmail_message_id(db_session):
    """Test unique constraint on gmail_message_id prevents duplicates."""
    # Create user
    user = User(email="test@example.com", is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create first email
    email1 = EmailProcessingQueue(
        user_id=user.id,
        gmail_message_id="duplicate_msg_id",
        gmail_thread_id="thread_001",
        sender="sender@example.com",
        subject="Original Email",
        received_at=datetime.now(UTC),
        status="pending",
    )
    db_session.add(email1)
    await db_session.commit()

    # Attempt to create duplicate email with same gmail_message_id
    email2 = EmailProcessingQueue(
        user_id=user.id,
        gmail_message_id="duplicate_msg_id",  # Same message ID
        gmail_thread_id="thread_002",
        sender="different@example.com",
        subject="Duplicate Email",
        received_at=datetime.now(UTC),
        status="pending",
    )
    db_session.add(email2)

    # Expect IntegrityError from unique constraint
    with pytest.raises(IntegrityError) as exc_info:
        await db_session.commit()

    assert "unique constraint" in str(exc_info.value).lower() or "duplicate key" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_status_field_values(db_session):
    """Test status field accepts valid state values."""
    # Create user
    user = User(email="test@example.com", is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Test all valid status values
    valid_statuses = ["pending", "processing", "approved", "rejected", "completed"]

    for idx, status in enumerate(valid_statuses):
        email = EmailProcessingQueue(
            user_id=user.id,
            gmail_message_id=f"msg_{idx}",
            gmail_thread_id=f"thread_{idx}",
            sender="sender@example.com",
            subject=f"Email {idx}",
            received_at=datetime.now(UTC),
            status=status,
        )
        db_session.add(email)

    await db_session.commit()

    # Verify all emails were created with correct statuses
    statement = select(EmailProcessingQueue).where(EmailProcessingQueue.user_id == user.id)
    result = await db_session.execute(statement)
    emails = result.scalars().all()

    assert len(emails) == len(valid_statuses)
    assert {e.status for e in emails} == set(valid_statuses)


@pytest.mark.asyncio
async def test_cascade_delete_emails(db_session):
    """Test cascade delete: deleting user deletes associated emails."""
    # Create user
    user = User(email="test@example.com", is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    user_id = user.id

    # Create multiple emails
    for i in range(3):
        email = EmailProcessingQueue(
            user_id=user_id,
            gmail_message_id=f"msg_{i}",
            gmail_thread_id=f"thread_{i}",
            sender=f"sender{i}@example.com",
            subject=f"Email {i}",
            received_at=datetime.now(UTC),
            status="pending",
        )
        db_session.add(email)

    await db_session.commit()

    # Verify emails exist
    statement = select(EmailProcessingQueue).where(EmailProcessingQueue.user_id == user_id)
    result = await db_session.execute(statement)
    emails_before = result.scalars().all()
    assert len(emails_before) == 3

    # Delete user
    await db_session.delete(user)
    await db_session.commit()

    # Verify all associated emails were deleted via cascade
    statement = select(EmailProcessingQueue).where(EmailProcessingQueue.user_id == user_id)
    result = await db_session.execute(statement)
    emails_after = result.scalars().all()
    assert len(emails_after) == 0


@pytest.mark.asyncio
async def test_email_timestamps(db_session):
    """Test created_at and updated_at auto-populate."""
    # Create user
    user = User(email="test@example.com", is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create email
    email = EmailProcessingQueue(
        user_id=user.id,
        gmail_message_id="msg_001",
        gmail_thread_id="thread_001",
        sender="sender@example.com",
        subject="Test Email",
        received_at=datetime.now(UTC),
        status="pending",
    )
    db_session.add(email)
    await db_session.commit()
    await db_session.refresh(email)

    # Verify timestamps are set
    assert email.created_at is not None
    assert email.updated_at is not None
    assert isinstance(email.created_at, datetime)
    assert isinstance(email.updated_at, datetime)

    # Verify created_at is close to current time (within 5 seconds)
    time_diff = abs((datetime.now(UTC) - email.created_at.replace(tzinfo=UTC)).total_seconds())
    assert time_diff < 5, f"created_at timestamp is {time_diff}s off"


@pytest.mark.asyncio
async def test_default_status_pending(db_session):
    """Test that status defaults to 'pending' when not specified."""
    # Create user
    user = User(email="test@example.com", is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create email without explicitly setting status
    email = EmailProcessingQueue(
        user_id=user.id,
        gmail_message_id="msg_001",
        gmail_thread_id="thread_001",
        sender="sender@example.com",
        subject="Test Email",
        received_at=datetime.now(UTC),
    )
    db_session.add(email)
    await db_session.commit()
    await db_session.refresh(email)

    # Verify default status is 'pending'
    assert email.status == "pending"
