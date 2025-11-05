"""Unit tests for EmailService."""

from datetime import datetime, UTC

import pytest

from app.models.email import EmailProcessingQueue
from app.models.user import User
from app.services.email_service import EmailService


@pytest.mark.asyncio
async def test_get_emails_by_status(db_session):
    """Test fetching emails by status."""
    # Create test user
    user = User(email="test@example.com", is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create emails with different statuses
    email1 = EmailProcessingQueue(
        user_id=user.id,
        gmail_message_id="msg_001",
        gmail_thread_id="thread_001",
        sender="sender1@example.com",
        subject="Pending Email 1",
        received_at=datetime.now(UTC),
        status="pending",
    )
    email2 = EmailProcessingQueue(
        user_id=user.id,
        gmail_message_id="msg_002",
        gmail_thread_id="thread_002",
        sender="sender2@example.com",
        subject="Pending Email 2",
        received_at=datetime.now(UTC),
        status="pending",
    )
    email3 = EmailProcessingQueue(
        user_id=user.id,
        gmail_message_id="msg_003",
        gmail_thread_id="thread_003",
        sender="sender3@example.com",
        subject="Processing Email",
        received_at=datetime.now(UTC),
        status="processing",
    )
    db_session.add(email1)
    db_session.add(email2)
    db_session.add(email3)
    await db_session.commit()

    # Create service and query pending emails
    service = EmailService()
    pending_emails = await service.get_emails_by_status(user.id, "pending")

    # Verify results
    assert len(pending_emails) == 2
    assert all(e.status == "pending" for e in pending_emails)
    assert {e.gmail_message_id for e in pending_emails} == {"msg_001", "msg_002"}


@pytest.mark.asyncio
async def test_get_pending_emails(db_session):
    """Test convenience method for fetching pending emails."""
    # Create test user
    user = User(email="test@example.com", is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create emails
    pending_email = EmailProcessingQueue(
        user_id=user.id,
        gmail_message_id="msg_pending",
        gmail_thread_id="thread_001",
        sender="sender@example.com",
        subject="Pending",
        received_at=datetime.now(UTC),
        status="pending",
    )
    completed_email = EmailProcessingQueue(
        user_id=user.id,
        gmail_message_id="msg_completed",
        gmail_thread_id="thread_002",
        sender="sender@example.com",
        subject="Completed",
        received_at=datetime.now(UTC),
        status="completed",
    )
    db_session.add(pending_email)
    db_session.add(completed_email)
    await db_session.commit()

    # Query using convenience method
    service = EmailService()
    pending_emails = await service.get_pending_emails(user.id)

    # Verify only pending returned
    assert len(pending_emails) == 1
    assert pending_emails[0].status == "pending"
    assert pending_emails[0].gmail_message_id == "msg_pending"


@pytest.mark.asyncio
async def test_get_email_by_message_id(db_session):
    """Test finding email by Gmail message ID."""
    # Create test user
    user = User(email="test@example.com", is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create email
    email = EmailProcessingQueue(
        user_id=user.id,
        gmail_message_id="unique_msg_id_123",
        gmail_thread_id="thread_001",
        sender="sender@example.com",
        subject="Test Email",
        received_at=datetime.now(UTC),
        status="pending",
    )
    db_session.add(email)
    await db_session.commit()

    # Find by message ID
    service = EmailService()
    found_email = await service.get_email_by_message_id("unique_msg_id_123")

    # Verify found
    assert found_email is not None
    assert found_email.gmail_message_id == "unique_msg_id_123"
    assert found_email.user_id == user.id

    # Test not found
    not_found = await service.get_email_by_message_id("nonexistent_msg_id")
    assert not_found is None


@pytest.mark.asyncio
async def test_update_email_status(db_session):
    """Test updating email status."""
    # Create test user
    user = User(email="test@example.com", is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create email with initial status
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

    email_id = email.id

    # Update status
    service = EmailService()
    updated_email = await service.update_email_status(email_id, "processing")

    # Verify update
    assert updated_email.status == "processing"
    assert updated_email.id == email_id

    # Verify database was updated
    await db_session.refresh(email)
    assert email.status == "processing"


@pytest.mark.asyncio
async def test_update_email_status_not_found(db_session):
    """Test updating status for nonexistent email raises error."""
    service = EmailService()

    # Attempt to update nonexistent email
    with pytest.raises(ValueError, match="Email with ID 99999 not found"):
        await service.update_email_status(99999, "processing")


@pytest.mark.asyncio
async def test_get_emails_by_nonexistent_user(db_session):
    """Test fetching emails for user with no emails returns empty list."""
    # Create user but no emails
    user = User(email="test@example.com", is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    service = EmailService()
    emails = await service.get_emails_by_status(user.id, "pending")

    # Should return empty list
    assert emails == []


@pytest.mark.asyncio
async def test_get_emails_by_status_multiple_statuses(db_session):
    """Test that status filtering works correctly across multiple statuses."""
    # Create test user
    user = User(email="test@example.com", is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create emails with all valid statuses
    statuses = ["pending", "processing", "approved", "rejected", "completed"]
    for idx, status in enumerate(statuses):
        email = EmailProcessingQueue(
            user_id=user.id,
            gmail_message_id=f"msg_{idx}",
            gmail_thread_id=f"thread_{idx}",
            sender=f"sender{idx}@example.com",
            subject=f"Email {idx}",
            received_at=datetime.now(UTC),
            status=status,
        )
        db_session.add(email)
    await db_session.commit()

    # Query each status
    service = EmailService()
    for status in statuses:
        emails = await service.get_emails_by_status(user.id, status)
        assert len(emails) == 1
        assert emails[0].status == status


@pytest.mark.asyncio
async def test_get_emails_filters_by_user(db_session):
    """Test that queries only return emails for specified user."""
    # Create two users
    user1 = User(email="user1@example.com", is_active=True)
    user2 = User(email="user2@example.com", is_active=True)
    db_session.add(user1)
    db_session.add(user2)
    await db_session.commit()
    await db_session.refresh(user1)
    await db_session.refresh(user2)

    # Create emails for both users
    email1 = EmailProcessingQueue(
        user_id=user1.id,
        gmail_message_id="user1_msg_001",
        gmail_thread_id="thread_001",
        sender="sender@example.com",
        subject="User 1 Email",
        received_at=datetime.now(UTC),
        status="pending",
    )
    email2 = EmailProcessingQueue(
        user_id=user2.id,
        gmail_message_id="user2_msg_001",
        gmail_thread_id="thread_002",
        sender="sender@example.com",
        subject="User 2 Email",
        received_at=datetime.now(UTC),
        status="pending",
    )
    db_session.add(email1)
    db_session.add(email2)
    await db_session.commit()

    # Query emails for user1
    service = EmailService()
    user1_emails = await service.get_emails_by_status(user1.id, "pending")

    # Verify only user1's emails returned
    assert len(user1_emails) == 1
    assert user1_emails[0].user_id == user1.id
    assert user1_emails[0].gmail_message_id == "user1_msg_001"

    # Query emails for user2
    user2_emails = await service.get_emails_by_status(user2.id, "pending")

    # Verify only user2's emails returned
    assert len(user2_emails) == 1
    assert user2_emails[0].user_id == user2.id
    assert user2_emails[0].gmail_message_id == "user2_msg_001"
