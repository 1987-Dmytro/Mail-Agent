"""
Unit tests for ResponseGenerationService (Story 3.7)

Tests cover:
- AC #2: Response need classification
- AC #3: RAG context retrieval integration
- AC #4: Language detection integration
- AC #5: Tone detection integration
- AC #6: Prompt formatting integration
- AC #7: LLM response generation
- AC #8: Database persistence
- AC #9: Response quality validation
- AC #10: Status updates

Created: 2025-11-10
Epic: 3 (RAG System & Response Generation)
Story: 3.7 (AI Response Generation Service)
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from app.services.response_generation import ResponseGenerationService
from app.models.email import EmailProcessingQueue
from app.models.user import User
from app.services.database import DatabaseService
import pytest_asyncio
from sqlmodel import Session, select


# Test fixtures for sample data

@pytest.fixture
def mock_context_service():
    """Mock ContextRetrievalService for testing."""
    mock = AsyncMock()
    mock.retrieve_context = AsyncMock(return_value={
        "thread_history": [
            {
                "message_id": "msg1",
                "sender": "sender@example.com",
                "subject": "Test subject",
                "body": "Test email body",
                "date": "2025-11-09T10:00:00Z",
                "thread_id": "thread123"
            }
        ],
        "semantic_results": [
            {
                "message_id": "msg2",
                "sender": "similar@example.com",
                "subject": "Similar subject",
                "body": "Similar email content",
                "date": "2025-11-08T10:00:00Z",
                "thread_id": "thread456"
            }
        ],
        "metadata": {
            "thread_length": 1,
            "semantic_count": 1,
            "oldest_thread_date": "2025-11-09T10:00:00Z",
            "total_tokens_used": 250
        }
    })
    return mock


@pytest.fixture
def mock_language_service():
    """Mock LanguageDetectionService for testing."""
    mock = Mock()
    mock.detect = Mock(return_value=("de", 0.95))  # German with high confidence
    return mock


@pytest.fixture
def mock_tone_service():
    """Mock ToneDetectionService for testing."""
    mock = Mock()
    mock.detect_tone = Mock(return_value="formal")
    return mock


@pytest.fixture
def mock_llm_client():
    """Mock LLMClient for testing."""
    mock = Mock()
    mock.send_prompt = Mock(return_value="Sehr geehrte Damen und Herren,\n\nvielen Dank für Ihre Anfrage. Ich freue mich, Ihnen mitteilen zu können...\n\nMit freundlichen Grüßen")
    return mock


@pytest_asyncio.fixture
async def sample_personal_email(db_session, test_user: User) -> EmailProcessingQueue:
    """Create sample personal email with question."""
    email = EmailProcessingQueue(
        user_id=test_user.id,
        gmail_message_id="personal_msg_123",
        gmail_thread_id="thread_personal_123",
        sender="friend@example.com",
        subject="Can you help me with this?",
        received_at=datetime.now(UTC),
        status="pending"
    )

    db_session.add(email)
    await db_session.commit()
    await db_session.refresh(email)
    return email


@pytest_asyncio.fixture
async def sample_newsletter_email(db_session, test_user: User) -> EmailProcessingQueue:
    """Create sample newsletter email (should not generate response)."""
    email = EmailProcessingQueue(
        user_id=test_user.id,
        gmail_message_id="newsletter_msg_456",
        gmail_thread_id="thread_newsletter_456",
        sender="noreply@newsletter.com",
        subject="Weekly Newsletter - Tech Updates",
        received_at=datetime.now(UTC),
        status="pending"
    )

    db_session.add(email)
    await db_session.commit()
    await db_session.refresh(email)
    return email


# Test 1: AC #2 - Personal email with questions → True

@pytest.mark.asyncio
async def test_should_generate_response_personal_email(
    sample_personal_email: EmailProcessingQueue,
    mock_context_service,
    mock_language_service,
    mock_tone_service,
    mock_llm_client
):
    """Test response classification for personal email with questions (AC #2).

    Expected: Returns True (should generate response)
    """
    service = ResponseGenerationService(
        user_id=sample_personal_email.user_id,
        context_service=mock_context_service,
        language_service=mock_language_service,
        tone_service=mock_tone_service,
        llm_client=mock_llm_client
    )

    result = await service.should_generate_response(sample_personal_email)

    assert result is True, "Personal email with question should trigger response generation"


# Test 2: AC #2 - Newsletter → False

@pytest.mark.asyncio
async def test_should_generate_response_newsletter(
    sample_newsletter_email: EmailProcessingQueue,
    mock_context_service,
    mock_language_service,
    mock_tone_service,
    mock_llm_client
):
    """Test response classification for automated newsletter (AC #2).

    Expected: Returns False (skip response generation)
    """
    service = ResponseGenerationService(
        user_id=sample_newsletter_email.user_id,
        context_service=mock_context_service,
        language_service=mock_language_service,
        tone_service=mock_tone_service,
        llm_client=mock_llm_client
    )

    result = await service.should_generate_response(sample_newsletter_email)

    assert result is False, "Newsletter email should NOT trigger response generation"


# Test 3: AC #2 - No-reply sender → False

@pytest.mark.asyncio
async def test_should_generate_response_noreply_email(
    db_session,
    test_user: User,
    mock_context_service,
    mock_language_service,
    mock_tone_service,
    mock_llm_client
):
    """Test response classification for no-reply sender (AC #2).

    Expected: Returns False (skip response generation)
    """
    # Create no-reply email
    noreply_email = EmailProcessingQueue(
        user_id=test_user.id,
        gmail_message_id="noreply_msg_789",
        gmail_thread_id="thread_noreply_789",
        sender="no-reply@automated-system.com",
        subject="Automated Notification",
        received_at=datetime.now(UTC),
        status="pending"
    )

    db_session.add(noreply_email)
    await db_session.commit()
    await db_session.refresh(noreply_email)

    service = ResponseGenerationService(
        user_id=test_user.id,
        context_service=mock_context_service,
        language_service=mock_language_service,
        tone_service=mock_tone_service,
        llm_client=mock_llm_client
    )

    result = await service.should_generate_response(noreply_email)

    assert result is False, "No-reply email should NOT trigger response generation"


# Test 4: AC #3 - RAG context retrieval integration

@pytest.mark.asyncio
async def test_generate_response_with_rag_context(
    sample_personal_email: EmailProcessingQueue,
    mock_context_service,
    mock_language_service,
    mock_tone_service,
    mock_llm_client,
    db_session
):
    """Test RAG context retrieval integration (AC #3).

    Expected: Service calls ContextRetrievalService.retrieve_context() with email_id
    """
    # Mock format_response_prompt and database session
    mock_db_session = Mock()
    mock_db_session.get = Mock(return_value=sample_personal_email)
    mock_db_session.__enter__ = Mock(return_value=mock_db_session)
    mock_db_session.__exit__ = Mock(return_value=False)

    with patch('app.services.response_generation.format_response_prompt', return_value="Mocked prompt"):
        with patch('app.services.response_generation.Session', return_value=mock_db_session):
            service = ResponseGenerationService(
                user_id=sample_personal_email.user_id,
                context_service=mock_context_service,
                language_service=mock_language_service,
                tone_service=mock_tone_service,
                llm_client=mock_llm_client,
                db_service=DatabaseService()
            )

            response = await service.generate_response(sample_personal_email.id)

            # Verify ContextRetrievalService was called
            mock_context_service.retrieve_context.assert_called_once_with(sample_personal_email.id)

            # Verify response generated
            assert response is not None
            assert len(response) > 0


# Test 5: AC #4 - Language detection integration

@pytest.mark.asyncio
async def test_generate_response_language_detection(
    sample_personal_email: EmailProcessingQueue,
    mock_context_service,
    mock_language_service,
    mock_tone_service,
    mock_llm_client
):
    """Test language detection integration (AC #4).

    Expected: Service calls LanguageDetectionService.detect() with email text
    """
    # Mock database session
    mock_db_session = Mock()
    mock_db_session.get = Mock(return_value=sample_personal_email)
    mock_db_session.__enter__ = Mock(return_value=mock_db_session)
    mock_db_session.__exit__ = Mock(return_value=False)

    with patch('app.services.response_generation.format_response_prompt', return_value="Mocked prompt"):
        with patch('app.services.response_generation.Session', return_value=mock_db_session):
            service = ResponseGenerationService(
                user_id=sample_personal_email.user_id,
                context_service=mock_context_service,
                language_service=mock_language_service,
                tone_service=mock_tone_service,
                llm_client=mock_llm_client,
                db_service=DatabaseService()
            )

            response = await service.generate_response(sample_personal_email.id)

            # Verify LanguageDetectionService was called
            mock_language_service.detect.assert_called()

            # Verify response generated with detected language
            assert response is not None


# Test 6: AC #5 - Tone detection integration

@pytest.mark.asyncio
async def test_generate_response_tone_detection(
    sample_personal_email: EmailProcessingQueue,
    mock_context_service,
    mock_language_service,
    mock_tone_service,
    mock_llm_client
):
    """Test tone detection integration (AC #5).

    Expected: Service calls ToneDetectionService.detect_tone() with email
    """
    # Mock database session
    mock_db_session = Mock()
    mock_db_session.get = Mock(return_value=sample_personal_email)
    mock_db_session.__enter__ = Mock(return_value=mock_db_session)
    mock_db_session.__exit__ = Mock(return_value=False)

    with patch('app.services.response_generation.format_response_prompt', return_value="Mocked prompt"):
        with patch('app.services.response_generation.Session', return_value=mock_db_session):
            service = ResponseGenerationService(
                user_id=sample_personal_email.user_id,
                context_service=mock_context_service,
                language_service=mock_language_service,
                tone_service=mock_tone_service,
                llm_client=mock_llm_client,
                db_service=DatabaseService()
            )

            response = await service.generate_response(sample_personal_email.id)

            # Verify ToneDetectionService was called
            mock_tone_service.detect_tone.assert_called()

            # Verify response generated with detected tone
            assert response is not None


# Test 7: AC #6 - Prompt formatting with format_response_prompt

@pytest.mark.asyncio
async def test_generate_response_prompt_formatting(
    sample_personal_email: EmailProcessingQueue,
    mock_context_service,
    mock_language_service,
    mock_tone_service,
    mock_llm_client
):
    """Test prompt construction with format_response_prompt (AC #6).

    Expected: Service calls format_response_prompt() with email, RAG context, language, tone
    """
    mock_format_prompt = Mock(return_value="Formatted prompt for Gemini")

    # Mock database session
    mock_db_session = Mock()
    mock_db_session.get = Mock(return_value=sample_personal_email)
    mock_db_session.__enter__ = Mock(return_value=mock_db_session)
    mock_db_session.__exit__ = Mock(return_value=False)

    with patch('app.services.response_generation.format_response_prompt', mock_format_prompt):
        with patch('app.services.response_generation.Session', return_value=mock_db_session):
            service = ResponseGenerationService(
                user_id=sample_personal_email.user_id,
                context_service=mock_context_service,
                language_service=mock_language_service,
                tone_service=mock_tone_service,
                llm_client=mock_llm_client,
                db_service=DatabaseService()
            )

            response = await service.generate_response(sample_personal_email.id)

            # Verify format_response_prompt was called
            mock_format_prompt.assert_called_once()
            call_args = mock_format_prompt.call_args

            # Verify correct parameters passed
            assert call_args is not None
            assert call_args.kwargs['language'] == 'de'
            assert call_args.kwargs['tone'] == 'formal'

            # Verify LLM was called with formatted prompt
            mock_llm_client.send_prompt.assert_called_once_with(
                prompt="Formatted prompt for Gemini",
                response_format="text",
                operation="response_generation"
            )


# Test 8: AC #9 - Valid response passes validation

def test_validate_response_success(
    mock_context_service,
    mock_language_service,
    mock_tone_service,
    mock_llm_client
):
    """Test valid response passes validation (AC #9).

    Expected: Returns True for response with correct length, language, and structure
    """
    service = ResponseGenerationService(
        user_id=1,
        context_service=mock_context_service,
        language_service=mock_language_service,
        tone_service=mock_tone_service,
        llm_client=mock_llm_client
    )

    valid_response = "Sehr geehrte Damen und Herren,\n\nvielen Dank für Ihre Nachricht. Ich freue mich, Ihnen mitteilen zu können, dass wir Ihre Anfrage bearbeitet haben.\n\nMit freundlichen Grüßen"

    result = service.validate_response(valid_response, expected_language="de")

    assert result is True, "Valid response with correct length, language, and structure should pass validation"


# Test 9: AC #9 - Validation catches invalid responses

def test_validate_response_failures(
    mock_context_service,
    mock_language_service,
    mock_tone_service,
    mock_llm_client
):
    """Test validation catches empty, too short, and wrong language responses (AC #9).

    Expected: Returns False for invalid responses
    """
    service = ResponseGenerationService(
        user_id=1,
        context_service=mock_context_service,
        language_service=mock_language_service,
        tone_service=mock_tone_service,
        llm_client=mock_llm_client
    )

    # Test 1: Empty response
    result_empty = service.validate_response("", expected_language="de")
    assert result_empty is False, "Empty response should fail validation"

    # Test 2: Too short response (< 50 chars)
    result_short = service.validate_response("Short", expected_language="de")
    assert result_short is False, "Too short response should fail validation"

    # Test 3: Too long response (> 2000 chars)
    long_response = "x" * 2500
    result_long = service.validate_response(long_response, expected_language="de")
    assert result_long is False, "Too long response should fail validation"

    # Test 4: Wrong language
    mock_language_service.detect = Mock(return_value=("en", 0.95))  # Detected English
    result_wrong_lang = service.validate_response(
        "This is an English response that is long enough to pass length checks but has wrong language",
        expected_language="de"  # Expected German
    )
    assert result_wrong_lang is False, "Response with wrong language should fail validation"


# Test 10: AC #8, #10 - Database persistence and status update

@pytest.mark.asyncio
async def test_save_response_draft_database(
    sample_personal_email: EmailProcessingQueue,
    mock_context_service,
    mock_language_service,
    mock_tone_service,
    mock_llm_client,
    db_session
):
    """Test database persistence and status update (AC #8, #10).

    Expected: Updates draft_response, detected_language, status, classification in database
    """
    response_draft = "Sehr geehrte Damen und Herren,\n\nvielen Dank für Ihre Anfrage.\n\nMit freundlichen Grüßen"
    language = "de"
    tone = "formal"

    # Mock database session
    mock_db_session = Mock()
    mock_db_session.get = Mock(return_value=sample_personal_email)
    mock_db_session.add = Mock()
    mock_db_session.commit = Mock()
    mock_db_session.__enter__ = Mock(return_value=mock_db_session)
    mock_db_session.__exit__ = Mock(return_value=False)

    with patch('app.services.response_generation.Session', return_value=mock_db_session):
        service = ResponseGenerationService(
            user_id=sample_personal_email.user_id,
            context_service=mock_context_service,
            language_service=mock_language_service,
            tone_service=mock_tone_service,
            llm_client=mock_llm_client,
            db_service=DatabaseService()
        )

        # Save response draft
        service.save_response_draft(
            email_id=sample_personal_email.id,
            response_draft=response_draft,
            language=language,
            tone=tone
        )

    # Verify email object was updated with correct values
    assert sample_personal_email.draft_response == response_draft, "draft_response should be saved"
    assert sample_personal_email.detected_language == language, "detected_language should be saved"
    assert sample_personal_email.status == "awaiting_approval", "status should be awaiting_approval (AC #10)"
    assert sample_personal_email.classification == "needs_response", "classification should be needs_response (AC #10)"
    assert sample_personal_email.updated_at is not None, "updated_at should be set"

    # Verify database operations were called
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
