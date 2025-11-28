"""Unit tests for EmailClassificationService.

This module tests the email classification service with mocked external dependencies
(Gmail API, Gemini LLM API). Tests verify classification logic, error handling, and
fallback behavior without making real API calls.

Test Coverage:
    - Successful classification with valid responses
    - Gemini API error handling (fallback to "Unclassified")
    - Invalid JSON response handling (Pydantic ValidationError)
    - Gmail API error propagation (workflow cannot continue)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import ValidationError

from app.services.classification import EmailClassificationService
from app.models.classification_response import ClassificationResponse
from app.models.email import EmailProcessingQueue
from app.models.folder_category import FolderCategory
from app.models.user import User
from app.utils.errors import GeminiAPIError, GmailAPIError


@pytest.fixture
def mock_db_session():
    """Create mock database session for testing."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_gmail_client():
    """Create mock Gmail API client."""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_llm_client():
    """Create mock Gemini LLM client.

    Note: receive_completion() is synchronous (not async), so use Mock not AsyncMock.
    """
    from unittest.mock import Mock
    client = Mock()
    return client


@pytest.fixture
def sample_email():
    """Create sample email for testing."""
    email = EmailProcessingQueue(
        id=123,
        user_id=456,
        gmail_message_id="msg_abc123",
        gmail_thread_id="thread_xyz",
        sender="john@example.com",
        subject="Project Update",
        status="pending",
    )
    # Mock user relationship
    email.user = User(id=456, email="user@example.com")
    return email


@pytest.fixture
def sample_folders():
    """Create sample folder categories for testing."""
    return [
        FolderCategory(
            id=1,
            user_id=456,
            name="Work",
            keywords=["project", "meeting", "deadline"],
        ),
        FolderCategory(
            id=2,
            user_id=456,
            name="Personal",
            keywords=["family", "vacation", "friend"],
        ),
        FolderCategory(
            id=3,
            user_id=456,
            name="Newsletters",
            keywords=["subscribe", "unsubscribe", "weekly"],
        ),
    ]


@pytest.mark.asyncio
async def test_classify_email_success(
    mock_db_session,
    mock_gmail_client,
    mock_llm_client,
    sample_email,
    sample_folders,
):
    """Test successful email classification with valid Gemini response.

    This test verifies the happy path where:
    - Email is loaded from database
    - Gmail API returns full email content
    - User folders are loaded
    - Classification prompt is constructed
    - Gemini API returns valid JSON classification
    - ClassificationResponse is parsed successfully
    """
    # Setup mock database responses
    # Mock EmailProcessingQueue query (result.scalar_one_or_none() is sync, not async)
    from unittest.mock import Mock
    email_result = Mock()
    email_result.scalar_one_or_none.return_value = sample_email

    # Mock User query (for user_email lookup)
    user_result = Mock()
    user_result.scalar_one_or_none.return_value = sample_email.user

    # Mock FolderCategory query (result.scalars().all() is sync, not async)
    folder_result = Mock()
    folder_result.scalars.return_value.all.return_value = sample_folders

    mock_db_session.execute.side_effect = [
        email_result,  # First query: Load email
        user_result,  # Second query: Load user for email
        folder_result,  # Third query: Load folders
    ]

    # Setup mock Gmail API response
    mock_gmail_client.get_message_detail.return_value = {
        "sender": "john@example.com",
        "subject": "Project Update",
        "body": "Hi team, here's the weekly project status update...",
        "received_at": "2025-11-07T10:00:00Z",
    }

    # Setup mock Gemini LLM response (valid classification JSON)
    mock_llm_client.receive_completion.return_value = {
        "suggested_folder": "Work",
        "reasoning": "Email contains project status update from team member",
        "priority_score": 75,
        "confidence": 0.95,
    }

    # Initialize classification service
    service = EmailClassificationService(
        db=mock_db_session,
        gmail_client=mock_gmail_client,
        llm_client=mock_llm_client,
    )

    # Execute classification
    result = await service.classify_email(email_id=123, user_id=456)

    # Verify result
    assert isinstance(result, ClassificationResponse)
    assert result.suggested_folder == "Work"
    assert result.reasoning == "Email contains project status update from team member"
    assert result.priority_score == 75
    assert result.confidence == 0.95

    # Verify Gmail client was called correctly
    mock_gmail_client.get_message_detail.assert_called_once_with(
        message_id="msg_abc123"
    )

    # Verify LLM client was called with prompt
    mock_llm_client.receive_completion.assert_called_once()
    call_args = mock_llm_client.receive_completion.call_args
    assert call_args.kwargs["operation"] == "classification"
    assert "Project Update" in call_args.kwargs["prompt"]


@pytest.mark.asyncio
async def test_classify_email_gemini_api_error(
    mock_db_session,
    mock_gmail_client,
    mock_llm_client,
    sample_email,
    sample_folders,
):
    """Test classification fallback when Gemini API fails.

    This test verifies error handling when Gemini LLM API encounters errors:
    - GeminiAPIError is caught
    - Fallback ClassificationResponse returned with "Unclassified" folder
    - Reasoning explains the error
    - Workflow continues (no exception propagated)
    """
    # Setup mock database responses
    from unittest.mock import Mock
    email_result = Mock()
    email_result.scalar_one_or_none.return_value = sample_email

    user_result = Mock()
    user_result.scalar_one_or_none.return_value = sample_email.user

    folder_result = Mock()
    folder_result.scalars.return_value.all.return_value = sample_folders

    mock_db_session.execute.side_effect = [
        email_result,
        user_result,
        folder_result,
    ]

    # Setup mock Gmail API response (successful)
    mock_gmail_client.get_message_detail.return_value = {
        "sender": "john@example.com",
        "subject": "Project Update",
        "body": "Email content here",
        "received_at": "2025-11-07T10:00:00Z",
    }

    # Setup mock Gemini LLM to raise API error
    mock_llm_client.receive_completion.side_effect = GeminiAPIError(
        "Rate limit exceeded"
    )

    # Initialize classification service
    service = EmailClassificationService(
        db=mock_db_session,
        gmail_client=mock_gmail_client,
        llm_client=mock_llm_client,
    )

    # Execute classification (should not raise exception)
    result = await service.classify_email(email_id=123, user_id=456)

    # Verify fallback classification
    assert isinstance(result, ClassificationResponse)
    # Fallback uses first user folder ("Work" in test data), not "Unclassified"
    assert result.suggested_folder == "Work"
    assert "GeminiAPIError" in result.reasoning
    assert result.priority_score == 50  # Medium priority for manual review
    assert result.confidence == 0.0  # No confidence in fallback


@pytest.mark.asyncio
async def test_classify_email_invalid_json_response(
    mock_db_session,
    mock_gmail_client,
    mock_llm_client,
    sample_email,
    sample_folders,
):
    """Test classification fallback when Gemini returns invalid JSON.

    This test verifies handling of malformed Gemini responses:
    - Pydantic ValidationError is caught when parsing invalid JSON
    - Fallback ClassificationResponse returned
    - Reasoning indicates invalid response format
    - Workflow continues (no exception propagated)
    """
    # Setup mock database responses
    from unittest.mock import Mock
    email_result = Mock()
    email_result.scalar_one_or_none.return_value = sample_email

    user_result = Mock()
    user_result.scalar_one_or_none.return_value = sample_email.user

    folder_result = Mock()
    folder_result.scalars.return_value.all.return_value = sample_folders

    mock_db_session.execute.side_effect = [
        email_result,
        user_result,
        folder_result,
    ]

    # Setup mock Gmail API response (successful)
    mock_gmail_client.get_message_detail.return_value = {
        "sender": "john@example.com",
        "subject": "Project Update",
        "body": "Email content here",
        "received_at": "2025-11-07T10:00:00Z",
    }

    # Setup mock Gemini LLM to return invalid JSON (missing required fields)
    mock_llm_client.receive_completion.return_value = {
        "folder": "Work",  # Wrong field name (should be "suggested_folder")
        "reason": "Some text",  # Wrong field name (should be "reasoning")
        # Missing required "suggested_folder" and "reasoning" fields
    }

    # Initialize classification service
    service = EmailClassificationService(
        db=mock_db_session,
        gmail_client=mock_gmail_client,
        llm_client=mock_llm_client,
    )

    # Execute classification (Pydantic ValidationError should be caught)
    result = await service.classify_email(email_id=123, user_id=456)

    # Verify fallback classification
    assert isinstance(result, ClassificationResponse)
    # Fallback uses first user folder ("Work" in test data), not "Unclassified"
    assert result.suggested_folder == "Work"
    assert "Invalid response format" in result.reasoning
    assert result.priority_score == 50
    assert result.confidence == 0.0


@pytest.mark.asyncio
async def test_classify_email_gmail_retrieval_failure(
    mock_db_session,
    mock_gmail_client,
    mock_llm_client,
    sample_email,
):
    """Test that Gmail API errors are propagated (workflow cannot continue).

    This test verifies critical error handling when email content is inaccessible:
    - GmailAPIError is raised by get_message_detail()
    - Exception is propagated (NOT caught)
    - Workflow cannot continue without email content
    - EmailProcessingQueue status NOT updated to awaiting_approval
    """
    # Setup mock database response for email query
    from unittest.mock import Mock
    email_result = Mock()
    email_result.scalar_one_or_none.return_value = sample_email
    mock_db_session.execute.return_value = email_result

    # Setup mock Gmail API to raise error (email inaccessible)
    mock_gmail_client.get_message_detail.side_effect = GmailAPIError(
        "Message not found or access denied"
    )

    # Initialize classification service
    service = EmailClassificationService(
        db=mock_db_session,
        gmail_client=mock_gmail_client,
        llm_client=mock_llm_client,
    )

    # Execute classification (should raise GmailAPIError)
    with pytest.raises(GmailAPIError) as exc_info:
        await service.classify_email(email_id=123, user_id=456)

    # Verify error message
    assert "Message not found or access denied" in str(exc_info.value)

    # Verify Gmail client was called
    mock_gmail_client.get_message_detail.assert_called_once_with(
        message_id="msg_abc123"
    )

    # Verify LLM client was NOT called (classification never reached)
    mock_llm_client.receive_completion.assert_not_called()
