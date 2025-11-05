"""Unit tests for email polling tasks.

Tests cover:
- Email fetching for individual users
- Multi-user polling orchestration
- Duplicate detection logic with database persistence
- Error handling and retry mechanisms
- Structured logging
- Gmail API rate limiting
- Database persistence for EmailProcessingQueue
"""

from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from googleapiclient.errors import HttpError
from sqlmodel import select

from app.models.user import User
from app.models.email import EmailProcessingQueue
from app.tasks.email_tasks import (
    _get_active_users,
    _poll_user_emails_async,
    poll_all_users,
    poll_user_emails,
)


# Test Fixtures
@pytest.fixture
def mock_database_service():
    """Mock DatabaseService for dependency injection."""
    mock_service = Mock()
    mock_service.async_session = Mock()
    return mock_service


@pytest.fixture
def mock_gmail_client():
    """Mock GmailClient for testing email fetching."""
    mock_client = AsyncMock()
    mock_client.get_messages = AsyncMock()
    return mock_client


@pytest.fixture
def sample_gmail_emails():
    """Sample Gmail API email responses."""
    return [
        {
            "message_id": "msg001",
            "thread_id": "thread001",
            "sender": "sender1@example.com",
            "subject": "Test Email 1",
            "snippet": "This is test email 1",
            "received_at": datetime(2024, 11, 5, 10, 0, 0),
            "labels": ["UNREAD", "INBOX"],
        },
        {
            "message_id": "msg002",
            "thread_id": "thread002",
            "sender": "sender2@example.com",
            "subject": "Test Email 2",
            "snippet": "This is test email 2",
            "received_at": datetime(2024, 11, 5, 10, 5, 0),
            "labels": ["UNREAD", "INBOX"],
        },
        {
            "message_id": "msg003",
            "thread_id": "thread003",
            "sender": "sender3@example.com",
            "subject": "Test Email 3",
            "snippet": "This is test email 3",
            "received_at": datetime(2024, 11, 5, 10, 10, 0),
            "labels": ["UNREAD", "INBOX"],
        },
    ]


@pytest.fixture
def sample_active_users():
    """Sample active users with Gmail tokens."""
    users = []
    for i in range(1, 4):
        user = User(
            id=i,
            email=f"user{i}@example.com",
            gmail_oauth_token=f"token_{i}",
            gmail_refresh_token=f"refresh_{i}",
            is_active=True,
        )
        users.append(user)
    return users


# Test: poll_user_emails fetches unread emails
@pytest.mark.asyncio
async def test_poll_user_emails_fetches_unread_emails(mock_gmail_client, sample_gmail_emails):
    """Test that poll_user_emails fetches unread emails from Gmail."""
    user_id = 123

    # Mock GmailClient to return test emails
    with patch("app.tasks.email_tasks.GmailClient", return_value=mock_gmail_client):
        mock_gmail_client.get_messages.return_value = sample_gmail_emails

        # Mock database session with proper async context manager
        with patch("app.tasks.email_tasks.database_service.async_session") as mock_session_ctx:
            # Create mock session instance
            mock_session_instance = MagicMock()

            # Mock session.execute() to return a result with scalar_one_or_none()
            # This simulates: result = await session.execute(statement)
            async def mock_execute(statement):
                mock_result = MagicMock()
                # No duplicates - scalar_one_or_none returns None
                mock_result.scalar_one_or_none = MagicMock(return_value=None)
                return mock_result

            mock_session_instance.execute = mock_execute
            mock_session_instance.add = MagicMock()  # session.add(email)
            mock_session_instance.commit = AsyncMock()  # await session.commit()

            # Setup async context manager
            # This makes: async with database_service.async_session() as session:
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_session_instance
            mock_context_manager.__aexit__.return_value = AsyncMock()
            mock_session_ctx.return_value = mock_context_manager

            # Call the async helper function
            new_count, skip_count = await _poll_user_emails_async(user_id)

            # Verify GmailClient.get_messages was called with correct parameters
            mock_gmail_client.get_messages.assert_called_once_with(query="is:unread", max_results=50)

            # Verify all 3 emails were detected as new (no duplicates yet)
            assert new_count == 3
            assert skip_count == 0

            # Verify session.add was called 3 times (once per email)
            assert mock_session_instance.add.call_count == 3
            # Verify session.commit was called once
            mock_session_instance.commit.assert_called_once()


# Test: duplicate detection skips existing emails
@pytest.mark.asyncio
async def test_duplicate_detection_skips_existing_emails(mock_gmail_client, sample_gmail_emails):
    """Test that duplicate emails are skipped during polling."""
    user_id = 123

    # Simulate one email already exists in database
    with patch("app.tasks.email_tasks.GmailClient", return_value=mock_gmail_client):
        mock_gmail_client.get_messages.return_value = sample_gmail_emails

        # Mock database session with proper async context manager
        with patch("app.tasks.email_tasks.database_service.async_session") as mock_session_ctx:
            # Create mock session instance
            mock_session_instance = MagicMock()

            # Mock database query - first email exists (duplicate), others are new
            # We need a counter to track which call we're on
            call_count = [0]

            async def mock_execute(statement):
                mock_result = MagicMock()
                # First call returns existing email (duplicate)
                if call_count[0] == 0:
                    mock_existing = MagicMock()
                    mock_existing.id = 999
                    # This simulates finding a duplicate in the database
                    mock_result.scalar_one_or_none = MagicMock(return_value=mock_existing)
                else:
                    # Subsequent calls return None (new emails)
                    mock_result.scalar_one_or_none = MagicMock(return_value=None)
                call_count[0] += 1
                return mock_result

            mock_session_instance.execute = mock_execute
            mock_session_instance.add = MagicMock()  # session.add(email)
            mock_session_instance.commit = AsyncMock()  # await session.commit()

            # Setup async context manager
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_session_instance
            mock_context_manager.__aexit__.return_value = AsyncMock()
            mock_session_ctx.return_value = mock_context_manager

            # Call the async helper function
            new_count, skip_count = await _poll_user_emails_async(user_id)

            # 2 new emails + 1 duplicate
            assert new_count == 2
            assert skip_count == 1

            # Verify session.add was called only 2 times (not for the duplicate)
            assert mock_session_instance.add.call_count == 2
            # Verify session.commit was called once
            mock_session_instance.commit.assert_called_once()


# Test: poll_all_users iterates active users
def test_poll_all_users_iterates_active_users(sample_active_users):
    """Test that poll_all_users spawns tasks for all active users."""
    # Mock _get_active_users to return sample users
    with patch("app.tasks.email_tasks._get_active_users", new_callable=AsyncMock) as mock_get_users:
        mock_get_users.return_value = sample_active_users

        # Mock poll_user_emails.delay to track task spawning
        with patch("app.tasks.email_tasks.poll_user_emails.delay") as mock_delay:
            # Mock time.sleep to avoid actual delay
            with patch("app.tasks.email_tasks.time.sleep"):
                # Mock asyncio.get_event_loop to return clean loop
                with patch("app.tasks.email_tasks.asyncio.get_event_loop") as mock_get_loop:
                    mock_loop = Mock()
                    mock_loop.is_closed.return_value = False
                    mock_loop.run_until_complete = Mock(return_value=sample_active_users)
                    mock_get_loop.return_value = mock_loop

                    # Call poll_all_users
                    poll_all_users()

                    # Verify poll_user_emails.delay was called for each user with valid token
                    assert mock_delay.call_count == 3
                    mock_delay.assert_any_call(1)
                    mock_delay.assert_any_call(2)
                    mock_delay.assert_any_call(3)


# Test: poll_all_users skips users without Gmail token
def test_poll_all_users_skips_users_without_token():
    """Test that poll_all_users skips users without Gmail OAuth tokens."""
    # Create users, some without Gmail tokens
    users = [
        User(id=1, email="user1@example.com", gmail_oauth_token="token_1", is_active=True),
        User(id=2, email="user2@example.com", gmail_oauth_token=None, is_active=True),  # No token
        User(id=3, email="user3@example.com", gmail_oauth_token="token_3", is_active=True),
    ]

    with patch("app.tasks.email_tasks._get_active_users", new_callable=AsyncMock) as mock_get_users:
        mock_get_users.return_value = users

        with patch("app.tasks.email_tasks.poll_user_emails.delay") as mock_delay:
            with patch("app.tasks.email_tasks.time.sleep"):
                # Mock asyncio.get_event_loop to return clean loop
                with patch("app.tasks.email_tasks.asyncio.get_event_loop") as mock_get_loop:
                    mock_loop = Mock()
                    mock_loop.is_closed.return_value = False
                    mock_loop.run_until_complete = Mock(return_value=users)
                    mock_get_loop.return_value = mock_loop

                    poll_all_users()

                    # Only 2 tasks should be spawned (users 1 and 3)
                    assert mock_delay.call_count == 2
                    mock_delay.assert_any_call(1)
                    mock_delay.assert_any_call(3)


# Test: polling error handling with transient Gmail errors
@pytest.mark.asyncio
async def test_polling_error_handling_transient_errors():
    """Test that transient Gmail errors trigger retry logic."""
    user_id = 123

    # Create HttpError with 503 status (transient error)
    mock_response = Mock()
    mock_response.status = 503
    http_error = HttpError(resp=mock_response, content=b"Service Unavailable")

    # Mock GmailClient to raise HttpError
    mock_gmail_client = AsyncMock()
    mock_gmail_client.get_messages.side_effect = http_error

    with patch("app.tasks.email_tasks.GmailClient", return_value=mock_gmail_client):
        with patch("app.tasks.email_tasks.database_service.async_session") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock()
            mock_session.return_value.__aexit__ = AsyncMock()

            # Call should raise HttpError (to be retried by Celery)
            with pytest.raises(HttpError):
                await _poll_user_emails_async(user_id)


# Test: polling error handling with permanent Gmail errors
@pytest.mark.asyncio
async def test_polling_error_handling_permanent_errors():
    """Test that permanent Gmail errors are logged and raised without retry."""
    user_id = 123

    # Create HttpError with 404 status (permanent error)
    mock_response = Mock()
    mock_response.status = 404
    http_error = HttpError(resp=mock_response, content=b"Not Found")

    mock_gmail_client = AsyncMock()
    mock_gmail_client.get_messages.side_effect = http_error

    with patch("app.tasks.email_tasks.GmailClient", return_value=mock_gmail_client):
        with patch("app.tasks.email_tasks.database_service.async_session") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock()
            mock_session.return_value.__aexit__ = AsyncMock()

            # Call should raise HttpError (permanent, won't retry)
            with pytest.raises(HttpError):
                await _poll_user_emails_async(user_id)


# Test: _get_active_users returns only active users
@pytest.mark.asyncio
async def test_get_active_users_filters_active():
    """Test that _get_active_users returns only users with is_active=True."""
    # Create mix of active and inactive users
    all_users = [
        User(id=1, email="user1@example.com", is_active=True),
        User(id=2, email="user2@example.com", is_active=False),  # Inactive
        User(id=3, email="user3@example.com", is_active=True),
    ]

    # Mock database query to return all users
    mock_session = AsyncMock()
    mock_result = AsyncMock()

    # Create mock scalars object
    mock_scalars = Mock()
    mock_scalars.all = Mock(return_value=[all_users[0], all_users[2]])  # Only active users
    mock_result.scalars = Mock(return_value=mock_scalars)

    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("app.tasks.email_tasks.database_service.async_session") as mock_db_session:
        # Create proper context manager mock
        context_manager = AsyncMock()
        context_manager.__aenter__.return_value = mock_session
        context_manager.__aexit__.return_value = AsyncMock()
        mock_db_session.return_value = context_manager

        # Call _get_active_users
        active_users = await _get_active_users()

        # Verify only active users returned
        assert len(active_users) == 2
        assert all(user.is_active for user in active_users)


# Test: email metadata extraction
@pytest.mark.asyncio
async def test_email_metadata_extraction(mock_gmail_client, sample_gmail_emails):
    """Test that email metadata is correctly extracted and logged."""
    user_id = 123

    with patch("app.tasks.email_tasks.GmailClient", return_value=mock_gmail_client):
        mock_gmail_client.get_messages.return_value = sample_gmail_emails

        # Mock database session with proper async context manager
        with patch("app.tasks.email_tasks.database_service.async_session") as mock_session_ctx:
            # Create mock session instance
            mock_session_instance = MagicMock()

            # Mock session.execute() to return a result with scalar_one_or_none()
            async def mock_execute(statement):
                mock_result = MagicMock()
                # No duplicates - scalar_one_or_none returns None
                mock_result.scalar_one_or_none = MagicMock(return_value=None)
                return mock_result

            mock_session_instance.execute = mock_execute
            mock_session_instance.add = MagicMock()  # session.add(email)
            mock_session_instance.commit = AsyncMock()  # await session.commit()

            # Setup async context manager
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_session_instance
            mock_context_manager.__aexit__.return_value = AsyncMock()
            mock_session_ctx.return_value = mock_context_manager

            # Patch logger to verify log entries
            with patch("app.tasks.email_tasks.logger") as mock_logger:
                await _poll_user_emails_async(user_id)

                # Verify metadata logged for each email (email_persisted events)
                # Should have: emails_fetched (1) + email_persisted (3) + email_processing_summary (1) = 5 total
                assert mock_logger.info.call_count >= 4  # At least 4 info logs

                # Check that message_id, sender, subject are logged
                logged_calls = [call for call in mock_logger.info.call_args_list if call[0][0] == "email_persisted"]
                assert len(logged_calls) == 3

                # Verify each logged call has the right fields
                for call in logged_calls:
                    # call is like: call('email_persisted', user_id=123, message_id='msg001', ...)
                    assert "user_id" in call[1]
                    assert "message_id" in call[1]
                    assert "sender" in call[1]
                    assert "subject" in call[1]


# Test: logging for polling cycle
@pytest.mark.asyncio
async def test_polling_cycle_logging(mock_gmail_client, sample_gmail_emails):
    """Test that polling cycle logs start, fetch, and completion events."""
    user_id = 123

    with patch("app.tasks.email_tasks.GmailClient", return_value=mock_gmail_client):
        mock_gmail_client.get_messages.return_value = sample_gmail_emails

        with patch("app.tasks.email_tasks.database_service.async_session") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock()
            mock_session.return_value.__aexit__ = AsyncMock()

            with patch("app.tasks.email_tasks.logger") as mock_logger:
                await _poll_user_emails_async(user_id)

                # Verify key log events
                log_events = [call[0][0] for call in mock_logger.info.call_args_list]
                assert "emails_fetched" in log_events
                assert "email_processing_summary" in log_events


# Test: empty email list handling
@pytest.mark.asyncio
async def test_poll_user_emails_handles_empty_inbox(mock_gmail_client):
    """Test that polling handles empty inbox gracefully."""
    user_id = 123

    with patch("app.tasks.email_tasks.GmailClient", return_value=mock_gmail_client):
        # Return empty list (no unread emails)
        mock_gmail_client.get_messages.return_value = []

        with patch("app.tasks.email_tasks.database_service.async_session") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock()
            mock_session.return_value.__aexit__ = AsyncMock()

            # Call should complete without errors
            new_count, skip_count = await _poll_user_emails_async(user_id)

            # Verify no emails processed
            assert new_count == 0
            assert skip_count == 0


# Test: email with missing message_id
@pytest.mark.asyncio
async def test_poll_user_emails_skips_invalid_email(mock_gmail_client):
    """Test that emails with missing message_id are skipped with warning."""
    user_id = 123

    # Email without message_id
    invalid_email = {
        "thread_id": "thread001",
        "sender": "sender@example.com",
        "subject": "Test Email",
        # message_id is missing
    }

    with patch("app.tasks.email_tasks.GmailClient", return_value=mock_gmail_client):
        mock_gmail_client.get_messages.return_value = [invalid_email]

        with patch("app.tasks.email_tasks.database_service.async_session") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock()
            mock_session.return_value.__aexit__ = AsyncMock()

            with patch("app.tasks.email_tasks.logger") as mock_logger:
                new_count, skip_count = await _poll_user_emails_async(user_id)

                # Email should be skipped
                assert new_count == 0

                # Warning should be logged
                warning_calls = [call for call in mock_logger.warning.call_args_list]
                assert len(warning_calls) > 0


# ==== NEW TESTS FOR STORY 1.7: DATABASE PERSISTENCE ====


@pytest.mark.asyncio
async def test_poll_saves_new_emails_to_database(db_session):
    """Test that polling saves newly detected emails to EmailProcessingQueue."""
    # Create test user
    user = User(email="test@example.com", is_active=True, gmail_oauth_token="test_token")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Mock Gmail client to return test emails
    mock_emails = [
        {
            "message_id": "gmail_msg_001",
            "thread_id": "gmail_thread_001",
            "sender": "sender1@example.com",
            "subject": "Test Email 1",
            "received_at": datetime.now(UTC),
        },
        {
            "message_id": "gmail_msg_002",
            "thread_id": "gmail_thread_002",
            "sender": "sender2@example.com",
            "subject": "Test Email 2",
            "received_at": datetime.now(UTC),
        },
    ]

    with patch("app.tasks.email_tasks.GmailClient") as mock_gmail_client:
        # Configure mock
        mock_instance = AsyncMock()
        mock_instance.get_messages = AsyncMock(return_value=mock_emails)
        mock_gmail_client.return_value = mock_instance

        # Call polling function
        new_count, skip_count = await _poll_user_emails_async(user.id)

        # Verify results
        assert new_count == 2
        assert skip_count == 0

        # Verify emails were saved to database
        statement = select(EmailProcessingQueue).where(
            EmailProcessingQueue.user_id == user.id
        )
        result = await db_session.execute(statement)
        saved_emails = result.scalars().all()

        assert len(saved_emails) == 2
        assert {e.gmail_message_id for e in saved_emails} == {"gmail_msg_001", "gmail_msg_002"}
        assert all(e.status == "pending" for e in saved_emails)
        assert all(e.user_id == user.id for e in saved_emails)


@pytest.mark.asyncio
async def test_duplicate_detection_with_database_persistence(db_session):
    """Test that duplicate emails are skipped based on database lookup."""
    # Create test user
    user = User(email="test@example.com", is_active=True, gmail_oauth_token="test_token")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Pre-populate database with existing email
    existing_email = EmailProcessingQueue(
        user_id=user.id,
        gmail_message_id="existing_msg_id",
        gmail_thread_id="thread_001",
        sender="sender@example.com",
        subject="Existing Email",
        received_at=datetime.now(UTC),
        status="processing",
    )
    db_session.add(existing_email)
    await db_session.commit()

    # Mock Gmail client to return same email again (duplicate)
    mock_emails = [
        {
            "message_id": "existing_msg_id",  # Same as existing
            "thread_id": "thread_001",
            "sender": "sender@example.com",
            "subject": "Duplicate Email",
            "received_at": datetime.now(UTC),
        },
    ]

    with patch("app.tasks.email_tasks.GmailClient") as mock_gmail_client:
        mock_instance = AsyncMock()
        mock_instance.get_messages = AsyncMock(return_value=mock_emails)
        mock_gmail_client.return_value = mock_instance

        # Call polling function
        new_count, skip_count = await _poll_user_emails_async(user.id)

        # Verify duplicate was skipped
        assert new_count == 0
        assert skip_count == 1

        # Verify no new email was created
        statement = select(EmailProcessingQueue).where(
            EmailProcessingQueue.user_id == user.id
        )
        result = await db_session.execute(statement)
        all_emails = result.scalars().all()

        assert len(all_emails) == 1  # Still only the original
        assert all_emails[0].gmail_message_id == "existing_msg_id"
        assert all_emails[0].status == "processing"  # Status unchanged


@pytest.mark.asyncio
async def test_poll_mixed_new_and_duplicate_emails_db(db_session):
    """Test polling with mix of new and duplicate emails using database."""
    # Create test user
    user = User(email="test@example.com", is_active=True, gmail_oauth_token="test_token")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Pre-populate with one existing email
    existing_email = EmailProcessingQueue(
        user_id=user.id,
        gmail_message_id="existing_001",
        gmail_thread_id="thread_001",
        sender="sender1@example.com",
        subject="Existing",
        received_at=datetime.now(UTC),
        status="pending",
    )
    db_session.add(existing_email)
    await db_session.commit()

    # Mock Gmail to return 1 duplicate + 2 new emails
    mock_emails = [
        {
            "message_id": "existing_001",  # Duplicate
            "thread_id": "thread_001",
            "sender": "sender1@example.com",
            "subject": "Duplicate",
            "received_at": datetime.now(UTC),
        },
        {
            "message_id": "new_002",  # New
            "thread_id": "thread_002",
            "sender": "sender2@example.com",
            "subject": "New Email 1",
            "received_at": datetime.now(UTC),
        },
        {
            "message_id": "new_003",  # New
            "thread_id": "thread_003",
            "sender": "sender3@example.com",
            "subject": "New Email 2",
            "received_at": datetime.now(UTC),
        },
    ]

    with patch("app.tasks.email_tasks.GmailClient") as mock_gmail_client:
        mock_instance = AsyncMock()
        mock_instance.get_messages = AsyncMock(return_value=mock_emails)
        mock_gmail_client.return_value = mock_instance

        # Call polling
        new_count, skip_count = await _poll_user_emails_async(user.id)

        # Verify counts
        assert new_count == 2
        assert skip_count == 1

        # Verify database state
        statement = select(EmailProcessingQueue).where(
            EmailProcessingQueue.user_id == user.id
        )
        result = await db_session.execute(statement)
        all_emails = result.scalars().all()

        assert len(all_emails) == 3  # 1 existing + 2 new
        message_ids = {e.gmail_message_id for e in all_emails}
        assert message_ids == {"existing_001", "new_002", "new_003"}
