"""Unit tests for EmailIndexingService.

This module tests the email history indexing service with mocked dependencies.

Test Coverage (AC mapped):
1. test_start_indexing_creates_progress_record (AC #1, #8)
2. test_retrieve_gmail_emails_90_day_filter (AC #2, #3)
3. test_process_batch_embeds_and_stores_50_emails (AC #4, #7)
4. test_extract_metadata_includes_all_fields (AC #5, #6)
5. test_resume_indexing_from_checkpoint (AC #9)
6. test_handle_error_updates_progress_status (AC #12)
7. test_mark_complete_updates_status (AC #10)
8. test_incremental_indexing_new_email (AC #11)

Reference: docs/stories/3-3-email-history-indexing.md
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch, call

from app.models.indexing_progress import IndexingProgress, IndexingStatus
from app.models.user import User
from app.services.email_indexing import EmailIndexingService


class TestEmailIndexingService:
    """Unit tests for EmailIndexingService."""

    @pytest.fixture
    def sample_embeddings(self):
        """Sample 768-dimensional embeddings (50 vectors)."""
        return [[0.1] * 768 for _ in range(50)]

    @pytest.mark.asyncio
    async def test_start_indexing_creates_progress_record(self):
        """Test that start_indexing creates IndexingProgress record (AC #1, #8)."""
        user_id = 123

        # Create mocks
        mock_db_service = MagicMock()
        mock_gmail_client = AsyncMock()
        mock_embedding_service = MagicMock()
        mock_vector_db_client = MagicMock()
        mock_telegram_bot = AsyncMock()

        service = EmailIndexingService(
            user_id=user_id,
            db_service=mock_db_service,
            gmail_client=mock_gmail_client,
            embedding_service=mock_embedding_service,
            vector_db_client=mock_vector_db_client,
            telegram_bot=mock_telegram_bot,
        )

        # Mock database session context
        mock_session = AsyncMock()
        mock_db_service.async_session.return_value.__aenter__.return_value = mock_session
        mock_db_service.async_session.return_value.__aexit__.return_value = AsyncMock()

        # Mock checking for existing progress (should return None)
        mock_check_result = MagicMock()
        mock_check_result.scalar_one_or_none.return_value = None

        # Mock final progress query
        mock_progress = IndexingProgress(
            id=1,
            user_id=user_id,
            total_emails=10,
            processed_count=10,
            status=IndexingStatus.COMPLETED,
        )
        mock_final_result = MagicMock()
        mock_final_result.scalar_one.return_value = mock_progress

        # Mock update_progress calls (need to handle nested session calls)
        mock_update_result = MagicMock()
        mock_update_result.scalar_one.return_value = IndexingProgress(
            id=1,
            user_id=user_id,
            total_emails=10,
            processed_count=0,
            status=IndexingStatus.IN_PROGRESS,
        )

        # Set up execute to return results asynchronously
        # Order: check existing, update progress (per batch), final query
        async def mock_execute_fn(*args, **kwargs):
            # Return next result from list
            if hasattr(mock_execute_fn, '_call_count'):
                mock_execute_fn._call_count += 1
            else:
                mock_execute_fn._call_count = 0

            results = [mock_check_result, mock_update_result, mock_final_result]
            if mock_execute_fn._call_count < len(results):
                return results[mock_execute_fn._call_count]
            return mock_final_result

        mock_session.execute = mock_execute_fn

        # Mock other methods
        service.retrieve_gmail_emails = AsyncMock(return_value=[
            {
                "message_id": f"msg_{i}",
                "thread_id": f"thread_{i}",
                "sender": f"sender{i}@example.com",
                "subject": f"Test {i}",
                "date": datetime.now(UTC),
                "body": "Test body",
                "snippet": "Test snippet",
            }
            for i in range(10)
        ])
        service.process_batch = AsyncMock(return_value=10)
        service.mark_complete = AsyncMock()
        service._send_completion_notification = AsyncMock()

        # Execute
        progress = await service.start_indexing(days_back=90)

        # Verify IndexingProgress was added
        assert mock_session.add.called
        added_progress = mock_session.add.call_args[0][0]
        assert isinstance(added_progress, IndexingProgress)
        assert added_progress.user_id == user_id
        assert added_progress.total_emails == 10

        # Verify final result
        assert progress.user_id == user_id
        assert progress.total_emails == 10

    @pytest.mark.asyncio
    async def test_retrieve_gmail_emails_90_day_filter(self):
        """Test that retrieve_gmail_emails applies 90-day filter and pagination (AC #2, #3)."""
        user_id = 123

        mock_db_service = MagicMock()
        mock_gmail_client = AsyncMock()

        service = EmailIndexingService(
            user_id=user_id,
            db_service=mock_db_service,
            gmail_client=mock_gmail_client,
            vector_db_client=MagicMock(),  # Provide mock to avoid init error
        )

        # Mock Gmail service
        mock_gmail_service = MagicMock()
        mock_gmail_client._get_gmail_service = AsyncMock(return_value=mock_gmail_service)
        mock_gmail_client._parse_gmail_date = lambda x: datetime.now(UTC)
        mock_gmail_client._extract_body = lambda x: "Test body"

        # Create sample messages
        sample_messages = [{"id": f"msg_{i}"} for i in range(5)]

        # Mock list() response (single page for simplicity)
        mock_list_result = {
            "messages": sample_messages,
            # No nextPageToken = single page
        }

        mock_gmail_service.users().messages().list().execute.return_value = mock_list_result

        # Mock get() for message details
        def create_message_detail(msg_id):
            return {
                "id": msg_id,
                "threadId": f"thread_0",
                "internalDate": str(int(datetime.now(UTC).timestamp() * 1000)),
                "snippet": "Test snippet",
                "payload": {
                    "headers": [
                        {"name": "From", "value": "sender@example.com"},
                        {"name": "Subject", "value": "Test Subject"},
                    ],
                    "body": {"data": ""},
                },
            }

        mock_gmail_service.users().messages().get().execute.side_effect = [
            create_message_detail(msg["id"]) for msg in sample_messages
        ]

        # Execute
        emails = await service.retrieve_gmail_emails(days_back=90)

        # Verify 90-day filter in query
        list_call = mock_gmail_service.users().messages().list.call_args
        assert list_call is not None
        call_kwargs = list_call[1]
        assert "q" in call_kwargs
        assert "after:" in call_kwargs["q"]  # Date filter present
        assert call_kwargs["maxResults"] == 100  # Batch size

        # Verify results
        assert len(emails) == 5

    @pytest.mark.asyncio
    async def test_process_batch_embeds_and_stores_50_emails(self, sample_embeddings):
        """Test that process_batch calls embed_batch and insert_embeddings_batch (AC #4, #7)."""
        user_id = 123

        mock_db_service = MagicMock()
        mock_embedding_service = MagicMock()
        mock_vector_db_client = MagicMock()

        service = EmailIndexingService(
            user_id=user_id,
            db_service=mock_db_service,
            embedding_service=mock_embedding_service,
            vector_db_client=mock_vector_db_client,
        )

        # Sample emails (50 for full batch)
        emails = [
            {
                "message_id": f"msg_{i}",
                "thread_id": f"thread_{i}",
                "sender": f"sender{i}@example.com",
                "subject": f"Test {i}",
                "date": datetime.now(UTC),
                "body": f"Email body {i}",
                "snippet": f"Snippet {i}",
            }
            for i in range(50)
        ]

        # Mock embedding generation
        mock_embedding_service.embed_batch.return_value = sample_embeddings

        # Mock vector DB insertion
        mock_vector_db_client.insert_embeddings_batch.return_value = True

        # Execute
        processed = await service.process_batch(emails)

        # Verify embed_batch called
        assert mock_embedding_service.embed_batch.called
        call_kwargs = mock_embedding_service.embed_batch.call_args[1]
        texts = call_kwargs["texts"]
        assert len(texts) == 50

        # Verify insert_embeddings_batch called
        assert mock_vector_db_client.insert_embeddings_batch.called
        call_kwargs = mock_vector_db_client.insert_embeddings_batch.call_args[1]
        assert call_kwargs["collection_name"] == "email_embeddings"
        assert len(call_kwargs["embeddings"]) == 50
        assert len(call_kwargs["metadatas"]) == 50

        # Verify return value
        assert processed == 50

    def test_extract_metadata_includes_all_fields(self):
        """Test that _extract_metadata includes all required fields (AC #5, #6)."""
        user_id = 123

        service = EmailIndexingService(
            user_id=user_id,
            db_service=MagicMock(),
            vector_db_client=MagicMock(),
        )

        # Sample email
        email = {
            "message_id": "msg_abc123",
            "thread_id": "thread_xyz789",
            "sender": "test@example.com",
            "subject": "Test Email Subject",
            "date": datetime(2025, 11, 9, 10, 0, 0, tzinfo=UTC),
            "body": "This is a test email body content. " * 10,  # > 200 chars
            "snippet": "This is a test email body content.",
        }

        # Execute
        metadata = service._extract_metadata(email)

        # Verify all fields present
        assert metadata["message_id"] == "msg_abc123"
        assert metadata["thread_id"] == "thread_xyz789"
        assert metadata["sender"] == "test@example.com"
        assert metadata["date"] == "2025-11-09"
        assert metadata["subject"] == "Test Email Subject"
        assert "language" in metadata
        assert "snippet" in metadata
        assert len(metadata["snippet"]) <= 200

    @pytest.mark.asyncio
    async def test_resume_indexing_from_checkpoint(self):
        """Test that resume_indexing continues from checkpoint (AC #9)."""
        user_id = 123

        mock_db_service = MagicMock()
        mock_gmail_client = AsyncMock()
        mock_embedding_service = MagicMock()
        mock_vector_db_client = MagicMock()
        mock_telegram_bot = AsyncMock()

        service = EmailIndexingService(
            user_id=user_id,
            db_service=mock_db_service,
            gmail_client=mock_gmail_client,
            embedding_service=mock_embedding_service,
            vector_db_client=mock_vector_db_client,
            telegram_bot=mock_telegram_bot,
        )

        # Mock database session
        mock_session = AsyncMock()
        mock_db_service.async_session.return_value.__aenter__.return_value = mock_session
        mock_db_service.async_session.return_value.__aexit__.return_value = AsyncMock()

        # Mock existing interrupted progress
        mock_progress = IndexingProgress(
            id=1,
            user_id=user_id,
            total_emails=100,
            processed_count=50,
            status=IndexingStatus.IN_PROGRESS,
            last_processed_message_id="msg_49",
        )

        mock_find_result = MagicMock()
        mock_find_result.scalar_one_or_none.return_value = mock_progress

        mock_progress_completed = IndexingProgress(
            id=1,
            user_id=user_id,
            total_emails=100,
            processed_count=100,
            status=IndexingStatus.COMPLETED,
        )
        mock_final_result = MagicMock()
        mock_final_result.scalar_one.return_value = mock_progress_completed

        async def mock_execute_fn(*args, **kwargs):
            if hasattr(mock_execute_fn, '_call_count'):
                mock_execute_fn._call_count += 1
            else:
                mock_execute_fn._call_count = 0
            results = [mock_find_result, mock_final_result]
            return results[min(mock_execute_fn._call_count, len(results) - 1)]

        mock_session.execute = mock_execute_fn

        # Mock retrieve remaining emails
        service.retrieve_gmail_emails = AsyncMock(return_value=[
            {"message_id": f"msg_{i}", "thread_id": f"thread_{i}", "sender": f"s{i}@ex.com",
             "subject": f"T{i}", "date": datetime.now(UTC), "body": "Test", "snippet": "Test"}
            for i in range(100)
        ])

        service.process_batch = AsyncMock(return_value=50)
        service.mark_complete = AsyncMock()
        service._send_completion_notification = AsyncMock()

        # Execute
        progress = await service.resume_indexing()

        # Verify result
        assert progress.status == IndexingStatus.COMPLETED
        assert service.mark_complete.called

    @pytest.mark.asyncio
    async def test_handle_error_updates_progress_status(self):
        """Test that handle_error updates progress status to failed (AC #12)."""
        user_id = 123

        mock_db_service = MagicMock()
        service = EmailIndexingService(
            user_id=user_id,
            db_service=mock_db_service,
            vector_db_client=MagicMock(),
        )

        # Mock database session
        mock_session = AsyncMock()
        mock_db_service.async_session.return_value.__aenter__.return_value = mock_session
        mock_db_service.async_session.return_value.__aexit__.return_value = AsyncMock()

        # Mock existing progress
        mock_progress = IndexingProgress(
            id=1,
            user_id=user_id,
            total_emails=100,
            processed_count=30,
            status=IndexingStatus.IN_PROGRESS,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_progress
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Execute
        test_error = ValueError("Test error message")
        await service.handle_error(test_error)

        # Verify status updated to PAUSED (not FAILED) for first error with retry logic
        assert mock_progress.status == IndexingStatus.PAUSED
        assert "ValueError: Test error message" in mock_progress.error_message
        assert mock_progress.retry_count == 1  # Incremented from 0 to 1
        assert mock_progress.retry_after is not None  # Should have retry_after set
        assert mock_session.commit.called

    @pytest.mark.asyncio
    async def test_mark_complete_updates_status(self):
        """Test that mark_complete updates status to completed (AC #10)."""
        user_id = 123

        mock_db_service = MagicMock()
        service = EmailIndexingService(
            user_id=user_id,
            db_service=mock_db_service,
            vector_db_client=MagicMock(),
        )

        # Mock database session
        mock_session = AsyncMock()
        mock_db_service.async_session.return_value.__aenter__.return_value = mock_session
        mock_db_service.async_session.return_value.__aexit__.return_value = AsyncMock()

        # Mock existing progress
        mock_progress = IndexingProgress(
            id=1,
            user_id=user_id,
            total_emails=100,
            processed_count=100,
            status=IndexingStatus.IN_PROGRESS,
            completed_at=None,
        )

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = mock_progress
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Execute
        await service.mark_complete()

        # Verify status updated
        assert mock_progress.status == IndexingStatus.COMPLETED
        assert mock_progress.completed_at is not None
        assert mock_session.commit.called

    @pytest.mark.asyncio
    async def test_incremental_indexing_new_email(self):
        """Test that index_new_email indexes single email immediately (AC #11)."""
        user_id = 123

        mock_db_service = MagicMock()
        mock_gmail_client = AsyncMock()
        mock_embedding_service = MagicMock()
        mock_vector_db_client = MagicMock()

        service = EmailIndexingService(
            user_id=user_id,
            db_service=mock_db_service,
            gmail_client=mock_gmail_client,
            embedding_service=mock_embedding_service,
            vector_db_client=mock_vector_db_client,
        )

        # Mock database session
        mock_session = AsyncMock()
        mock_db_service.async_session.return_value.__aenter__.return_value = mock_session
        mock_db_service.async_session.return_value.__aexit__.return_value = AsyncMock()

        # Mock initial indexing complete
        mock_progress = IndexingProgress(
            id=1,
            user_id=user_id,
            total_emails=100,
            processed_count=100,
            status=IndexingStatus.COMPLETED,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_progress
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Mock Gmail service
        mock_gmail_service = MagicMock()
        mock_gmail_client._get_gmail_service = AsyncMock(return_value=mock_gmail_service)

        mock_message = {
            "id": "msg_new",
            "threadId": "thread_new",
            "internalDate": str(int(datetime.now(UTC).timestamp() * 1000)),
            "snippet": "New email",
            "payload": {
                "headers": [
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "Subject", "value": "New Email"},
                ],
                "body": {"data": "VGVzdA=="},
            },
        }
        mock_gmail_service.users().messages().get().execute.return_value = mock_message

        # Mock process_batch
        service.process_batch = AsyncMock(return_value=1)

        # Execute
        success = await service.index_new_email(message_id="msg_new")

        # Verify success
        assert success is True
        assert service.process_batch.called
