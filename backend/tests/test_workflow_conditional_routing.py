"""
Unit tests for Story 3.11: Workflow Integration & Conditional Routing

This module tests the conditional routing logic and node implementations:
- route_by_classification() function (AC #2)
- classify node classification field setting (AC #1)
- draft_response node service integration (AC #3)
- send_telegram node template selection (AC #6)

Created: 2025-11-10
Epic: 3 (RAG System & Response Generation)
Story: 3.11 (Workflow Integration & Conditional Routing)
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from app.workflows.email_workflow import route_by_classification, route_after_approval
from app.workflows.states import EmailWorkflowState
from app.workflows.nodes import classify, draft_response, send_telegram
from app.models.email import EmailProcessingQueue


class TestRoutingLogic:
    """Unit tests for route_by_classification() function (Story 3.11 - AC #2)."""

    def test_route_by_classification_needs_response(self):
        """Test routing returns 'needs_response' classification for path mapping (AC #2).

        Verifies that emails classified as needing responses return the classification
        value which the path_map will route to the generate_response node.
        """
        # Arrange
        state = EmailWorkflowState(
            email_id="123",
            user_id="456",
            thread_id="test_thread",
            email_content="Can you help me with this?",
            sender="user@example.com",
            subject="Question about project",
            body_preview="Can you help me with this?",
            classification="needs_response",  # Key field for routing
            proposed_folder=None,
            proposed_folder_id=None,
            classification_reasoning=None,
            priority_score=50,
            draft_response=None,
            detected_language=None,
            tone=None,
            telegram_message_id=None,
            user_decision=None,
            selected_folder=None,
            selected_folder_id=None,
            final_action=None,
            error_message=None
        )

        # Act
        classification = route_by_classification(state)

        # Assert
        assert classification == "needs_response", (
            "Expected routing function to return classification value 'needs_response' "
            "which path_map will route to generate_response node"
        )

    def test_route_by_classification_sort_only(self):
        """Test routing returns 'sort_only' classification for path mapping (AC #2).

        Verifies that emails classified as sort-only (newsletters, notifications)
        return the classification value which the path_map will route directly to
        the send_telegram node, skipping response generation.
        """
        # Arrange
        state = EmailWorkflowState(
            email_id="123",
            user_id="456",
            thread_id="test_thread",
            email_content="Weekly newsletter",
            sender="newsletter@example.com",
            subject="Weekly Update",
            body_preview="Weekly newsletter",
            classification="sort_only",  # Key field for routing
            proposed_folder="Newsletters",
            proposed_folder_id=5,
            classification_reasoning="Newsletter from known sender",
            priority_score=30,
            draft_response=None,
            detected_language=None,
            tone=None,
            telegram_message_id=None,
            user_decision=None,
            selected_folder=None,
            selected_folder_id=None,
            final_action=None,
            error_message=None
        )

        # Act
        classification = route_by_classification(state)

        # Assert
        assert classification == "sort_only", (
            "Expected routing function to return classification value 'sort_only' "
            "which path_map will route to send_telegram node"
        )


class TestNodeLogic:
    """Unit tests for workflow node implementations (Story 3.11 - AC #1, #3, #6)."""

    @pytest.mark.asyncio
    async def test_classify_sets_classification_needs_response(self):
        """Test classify node sets classification field using ResponseGenerationService (AC #1).

        Verifies that the classify node calls ResponseGenerationService.should_generate_response()
        and correctly sets the classification field based on the result.
        """
        # Arrange
        state = EmailWorkflowState(
            email_id="123",
            user_id="456",
            thread_id="test_thread",
            email_content="Can you help me?",
            sender="user@example.com",
            subject="Need help",
            body_preview="Can you help me?",
            classification=None,  # Should be set by node
            proposed_folder=None,
            proposed_folder_id=None,
            classification_reasoning=None,
            priority_score=0,
            draft_response=None,
            detected_language=None,
            tone=None,
            telegram_message_id=None,
            user_decision=None,
            selected_folder=None,
            selected_folder_id=None,
            final_action=None,
            error_message=None
        )

        # Mock database with multiple query results
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()

        # Mock email from database
        mock_email = Mock(spec=EmailProcessingQueue)
        mock_email.id = 123
        mock_email.user_id = 456
        mock_email.sender = "user@example.com"
        mock_email.subject = "Need help"
        mock_email.gmail_message_id = "msg_123"

        # Create multiple results for multiple db.execute() calls
        # Important: scalar_one_or_none is SYNC, not async
        mock_result1 = Mock()
        mock_result1.scalar_one_or_none = Mock(return_value=mock_email)

        mock_result2 = Mock()
        mock_result2.scalar_one_or_none = Mock(return_value=None)  # Folder not found

        # Use a function instead of side_effect to handle unlimited queries
        query_count = [0]
        def mock_execute(query):
            query_count[0] += 1
            if query_count[0] == 1:
                return mock_result1
            else:
                return mock_result2

        # Return different results for different execute calls (db.execute IS async)
        mock_db.execute = AsyncMock(side_effect=mock_execute)

        # Create db_factory that returns mock_db as async context manager
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_db_factory():
            """Context manager factory that yields the mock session."""
            yield mock_db

        # Mock classification service
        mock_classification_service = AsyncMock()
        mock_classification_result = Mock()
        mock_classification_result.suggested_folder = "Work"
        mock_classification_result.reasoning = "Work-related email"
        mock_classification_result.priority_score = 50
        mock_classification_service.classify_email.return_value = mock_classification_result

        # Mock ResponseGenerationService to return True (needs response)
        with patch('app.workflows.nodes.EmailClassificationService', return_value=mock_classification_service):
            with patch('app.services.response_generation.ResponseGenerationService') as MockResponseService:
                mock_response_service = AsyncMock()
                mock_response_service.should_generate_response.return_value = True
                MockResponseService.return_value = mock_response_service

                # Mock gmail_client and llm_client
                mock_gmail = AsyncMock()
                mock_llm = Mock()

                # Act - Pass db_factory instead of db
                result_state = await classify(state, mock_db_factory, mock_gmail, mock_llm)

        # Assert
        assert result_state["classification"] == "needs_response", (
            "Expected classification to be set to needs_response when ResponseGenerationService "
            "returns True"
        )
        assert result_state["proposed_folder"] == "Work"
        assert result_state["priority_score"] == 50

    @pytest.mark.asyncio
    async def test_draft_response_calls_service(self):
        """Test draft_response node calls ResponseGenerationService and updates state (AC #3).

        Verifies that the draft_response node:
        1. Instantiates ResponseGenerationService for the user
        2. Calls generate_response() method
        3. Updates state with draft_response, detected_language, tone
        """
        # Arrange
        state = EmailWorkflowState(
            email_id="123",
            user_id="456",
            thread_id="test_thread",
            email_content="Can you help me?",
            sender="user@example.com",
            subject="Need help",
            body_preview="Can you help me?",
            classification="needs_response",
            proposed_folder="Work",
            proposed_folder_id=1,
            classification_reasoning="Work question",
            priority_score=50,
            draft_response=None,  # Should be set by node
            detected_language=None,  # Should be set by node
            tone=None,  # Should be set by node
            telegram_message_id=None,
            user_decision=None,
            selected_folder=None,
            selected_folder_id=None,
            final_action=None,
            error_message=None
        )

        # Mock database
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Mock email from database
        mock_email = Mock(spec=EmailProcessingQueue)
        mock_email.id = 123
        mock_email.user_id = 456
        mock_email.detected_language = "en"
        mock_email.tone = "professional"

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_email)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Create db_factory that returns mock_db as async context manager
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_db_factory():
            """Context manager factory that yields the mock session."""
            yield mock_db

        # Mock ResponseGenerationService
        mock_response_text = "Dear colleague, I'd be happy to help you with that. Best regards."

        # Mock ContextRetrievalService (for DI)
        mock_context_service = AsyncMock()

        with patch('app.services.response_generation.ResponseGenerationService') as MockResponseService:
            mock_service = AsyncMock()
            mock_service.generate_response.return_value = mock_response_text
            MockResponseService.return_value = mock_service

            # Act - Pass db_factory and mocked context_service for DI
            result_state = await draft_response(
                state,
                mock_db_factory,
                context_service=mock_context_service
            )

        # Assert
        assert result_state["draft_response"] == mock_response_text, (
            "Expected draft_response to be populated with generated response text"
        )
        assert result_state["detected_language"] == "en", (
            "Expected detected_language to be set from email metadata"
        )
        assert result_state["tone"] == "professional", (
            "Expected tone to be set from email metadata"
        )

        # Verify ResponseGenerationService was called correctly with injected context_service
        MockResponseService.assert_called_once_with(
            user_id=456,
            context_service=mock_context_service
        )
        mock_service.generate_response.assert_called_once_with(email_id=123)

    @pytest.mark.asyncio
    async def test_send_telegram_uses_correct_template(self):
        """Test send_telegram node selects appropriate template based on draft_response (AC #6).

        Verifies that send_telegram node:
        1. Checks if draft_response exists in state
        2. Uses TelegramResponseDraftService template when draft exists
        3. Uses existing sorting proposal template when no draft exists
        """
        # Arrange - State WITH draft_response
        state_with_draft = EmailWorkflowState(
            email_id="123",
            user_id="456",
            thread_id="test_thread",
            email_content="Can you help me?",
            sender="user@example.com",
            subject="Need help",
            body_preview="Can you help me?",
            classification="needs_response",
            proposed_folder="Work",
            proposed_folder_id=1,
            classification_reasoning="Work question",
            priority_score=75,  # Priority email to trigger immediate send
            draft_response="Dear colleague, I'd be happy to help. Best regards.",  # Draft exists
            detected_language="en",
            tone="professional",
            telegram_message_id=None,
            user_decision=None,
            selected_folder=None,
            selected_folder_id=None,
            final_action=None,
            error_message=None
        )

        # Mock database and telegram client
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_telegram = AsyncMock()
        mock_telegram.send_message_with_buttons.return_value = "telegram_msg_456"

        # Mock user from database
        mock_user = Mock()
        mock_user.id = 456
        mock_user.telegram_id = "telegram_user_789"

        # Mock email from database (for draft service)
        mock_email = Mock(spec=EmailProcessingQueue)
        mock_email.id = 123
        mock_email.user_id = 456
        mock_email.draft_response = "Dear colleague, I'd be happy to help. Best regards."
        mock_email.detected_language = "en"
        mock_email.tone = "professional"
        mock_email.sender = "user@example.com"
        mock_email.subject = "Need help"
        mock_email.is_priority = True

        # Create results for multiple db.execute() calls
        # Important: scalar_one_or_none is SYNC, not async
        user_result = Mock()
        user_result.scalar_one_or_none = Mock(return_value=mock_user)

        email_result = Mock()
        email_result.scalar_one_or_none = Mock(return_value=mock_email)

        # Return user result for first query, email result for subsequent queries (db.execute IS async)
        mock_db.execute = AsyncMock(side_effect=[user_result, email_result])

        # Create db_factory that returns mock_db as async context manager
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_db_factory():
            """Context manager factory that yields the mock session."""
            yield mock_db

        # Mock TelegramResponseDraftService
        with patch('app.services.telegram_response_draft.TelegramResponseDraftService') as MockDraftService:
            mock_draft_service = Mock()
            # format_response_draft_message is now async, so use AsyncMock
            mock_draft_service.format_response_draft_message = AsyncMock(return_value="Draft message text")
            mock_draft_service.build_response_draft_keyboard.return_value = [["Send", "Edit", "Reject"]]
            MockDraftService.return_value = mock_draft_service

            # Act - Pass db_factory instead of db
            result_state = await send_telegram(state_with_draft, mock_db_factory, mock_telegram)

            # Assert
            # Note: format_response_draft_message is called with email_id and additional parameters
            mock_draft_service.format_response_draft_message.assert_called_once()
            call_args_draft = mock_draft_service.format_response_draft_message.call_args
            assert call_args_draft.kwargs["email_id"] == 123

            mock_draft_service.build_response_draft_keyboard.assert_called_once_with(email_id=123)
            mock_telegram.send_message_with_buttons.assert_called_once()

            # Verify response draft template was used (message text should be draft message)
            call_args = mock_telegram.send_message_with_buttons.call_args
            assert call_args.kwargs["text"] == "Draft message text", (
                "Expected send_telegram to use TelegramResponseDraftService template when "
                "draft_response exists in state"
            )


class TestRouteAfterApproval:
    """Unit tests for route_after_approval() function (Story 1.2)."""

    def test_needs_response_approved_routes_to_send_email(self):
        """Test needs_response + approve routes to send_email_response (Story 1.2 - AC #1).

        Verifies that emails classified as needing responses and approved by user
        route to send_email_response node to send the AI-generated email.
        """
        # Arrange
        state = EmailWorkflowState(
            email_id="123",
            user_id="456",
            thread_id="test_thread",
            email_content="Can you help me with this?",
            sender="user@example.com",
            subject="Question about project",
            body_preview="Can you help me?",
            classification="needs_response",
            proposed_folder="Work",
            proposed_folder_id=1,
            classification_reasoning="Work question",
            priority_score=75,
            draft_response="I'd be happy to help. Let me look into that.",
            detected_language="en",
            tone="professional",
            telegram_message_id="msg_123",
            user_decision="approve",  # User approved
            selected_folder=None,
            selected_folder_id=None,
            final_action=None,
            error_message=None
        )

        # Act
        route = route_after_approval(state)

        # Assert
        assert route == "send_email", (
            "Expected route 'send_email' for needs_response emails that are approved, "
            "to send AI-generated email response before executing Gmail action"
        )

    def test_sort_only_approved_routes_to_execute_action(self):
        """Test sort_only + approve routes directly to execute_action (Story 1.2 - AC #2).

        Verifies that emails classified as sort-only and approved by user
        skip send_email_response and go directly to execute_action (Gmail label).
        This fixes the critical bug where ALL emails were getting email responses sent.
        """
        # Arrange
        state = EmailWorkflowState(
            email_id="124",
            user_id="456",
            thread_id="test_thread_2",
            email_content="Weekly newsletter",
            sender="newsletter@example.com",
            subject="Weekly Update",
            body_preview="Weekly newsletter",
            classification="sort_only",  # Sort only, no response needed
            proposed_folder="Newsletters",
            proposed_folder_id=5,
            classification_reasoning="Newsletter from known sender",
            priority_score=30,
            draft_response=None,  # No draft for sort_only
            detected_language=None,
            tone=None,
            telegram_message_id="msg_124",
            user_decision="approve",  # User approved
            selected_folder=None,
            selected_folder_id=None,
            final_action=None,
            error_message=None
        )

        # Act
        route = route_after_approval(state)

        # Assert
        assert route == "execute_only", (
            "Expected route 'execute_only' for sort_only emails that are approved, "
            "to skip email sending and go directly to execute_action (Gmail label)"
        )

    def test_rejection_routes_to_confirmation(self):
        """Test user rejection routes to send_confirmation (Story 1.2 - AC #3).

        Verifies that when user rejects an email (classification doesn't matter),
        workflow skips both send_email_response and execute_action, going directly
        to send_confirmation to notify user of rejection.
        """
        # Arrange
        state = EmailWorkflowState(
            email_id="125",
            user_id="456",
            thread_id="test_thread_3",
            email_content="Spam email",
            sender="spam@example.com",
            subject="Buy now!!!",
            body_preview="Spam email",
            classification="sort_only",
            proposed_folder="Spam",
            proposed_folder_id=6,
            classification_reasoning="Likely spam",
            priority_score=10,
            draft_response=None,
            detected_language=None,
            tone=None,
            telegram_message_id="msg_125",
            user_decision="reject",  # User rejected
            selected_folder=None,
            selected_folder_id=None,
            final_action=None,
            error_message=None
        )

        # Act
        route = route_after_approval(state)

        # Assert
        assert route == "reject", (
            "Expected route 'reject' when user rejects email, "
            "to skip all actions and go directly to send_confirmation"
        )

    def test_folder_change_with_needs_response_sends_email_first(self):
        """Test folder change + needs_response still sends email (Story 1.2 - AC #4).

        Verifies that when user changes folder for a needs_response email,
        the workflow still sends the AI-generated email response before
        executing the action with the user-selected folder.
        """
        # Arrange
        state = EmailWorkflowState(
            email_id="126",
            user_id="456",
            thread_id="test_thread_4",
            email_content="Can you help?",
            sender="user@example.com",
            subject="Question",
            body_preview="Can you help?",
            classification="needs_response",
            proposed_folder="Work",
            proposed_folder_id=1,
            classification_reasoning="Work question",
            priority_score=60,
            draft_response="I'd be happy to help.",
            detected_language="en",
            tone="professional",
            telegram_message_id="msg_126",
            user_decision="change_folder",  # User changed folder
            selected_folder="Personal",
            selected_folder_id=2,
            final_action=None,
            error_message=None
        )

        # Act
        route = route_after_approval(state)

        # Assert
        assert route == "send_email", (
            "Expected route 'send_email' when user changes folder for needs_response email, "
            "to send AI response before executing action with selected_folder"
        )

    def test_folder_change_with_sort_only_executes_action_only(self):
        """Test folder change + sort_only skips email send (Story 1.2 - AC #4).

        Verifies that when user changes folder for a sort_only email,
        the workflow skips email sending and goes directly to execute_action
        with the user-selected folder.
        """
        # Arrange
        state = EmailWorkflowState(
            email_id="127",
            user_id="456",
            thread_id="test_thread_5",
            email_content="Newsletter",
            sender="newsletter@example.com",
            subject="Update",
            body_preview="Newsletter",
            classification="sort_only",
            proposed_folder="Newsletters",
            proposed_folder_id=5,
            classification_reasoning="Newsletter",
            priority_score=20,
            draft_response=None,
            detected_language=None,
            tone=None,
            telegram_message_id="msg_127",
            user_decision="change_folder",  # User changed folder
            selected_folder="Archive",
            selected_folder_id=7,
            final_action=None,
            error_message=None
        )

        # Act
        route = route_after_approval(state)

        # Assert
        assert route == "execute_only", (
            "Expected route 'execute_only' when user changes folder for sort_only email, "
            "to skip email sending and execute action with selected_folder"
        )
