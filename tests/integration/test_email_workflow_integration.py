"""Integration tests for LangGraph email classification workflow.

This module tests the complete workflow execution with real database interactions
but mocked external APIs (Gmail, Gemini, Telegram). Tests verify workflow state
management, checkpoint persistence, and database updates.

Test Coverage:
    - Workflow state transitions through all nodes
    - PostgreSQL checkpoint persistence and resumption
    - Classification results stored in EmailProcessingQueue
    - Workflow error handling with fallback classification

Integration Test Setup:
    - Uses test database for real database operations
    - Mocks external APIs (Gmail, Gemini, Telegram)
    - Marks tests with @pytest.mark.integration for optional execution
    - Run with: pytest -v --integration
"""

import os
import uuid
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from sqlalchemy import select

from app.services.workflow_tracker import WorkflowInstanceTracker
from app.models.email import EmailProcessingQueue
from app.models.folder_category import FolderCategory
from app.models.user import User
from app.utils.errors import GeminiAPIError


@pytest.fixture
async def test_user(async_db_session):
    """Create test user in database."""
    user = User(
        email="test@example.com",
        hashed_password="hashed_pwd",
        is_active=True,
        onboarding_completed=True,
    )
    async_db_session.add(user)
    await async_db_session.commit()
    await async_db_session.refresh(user)
    return user


@pytest.fixture
async def test_folders(async_db_session, test_user):
    """Create test folder categories in database."""
    folders = [
        FolderCategory(
            user_id=test_user.id,
            name="Work",
            keywords=["project", "meeting"],
            is_default=False,
        ),
        FolderCategory(
            user_id=test_user.id,
            name="Personal",
            keywords=["family", "friend"],
            is_default=False,
        ),
        FolderCategory(
            user_id=test_user.id,
            name="Unclassified",
            keywords=[],
            is_default=True,
        ),
    ]
    for folder in folders:
        async_db_session.add(folder)
    await async_db_session.commit()
    return folders


@pytest.fixture
async def test_email(async_db_session, test_user):
    """Create test email in EmailProcessingQueue."""
    email = EmailProcessingQueue(
        user_id=test_user.id,
        gmail_message_id=f"test_msg_{uuid.uuid4()}",
        gmail_thread_id="thread_test_123",
        sender="sender@example.com",
        subject="Test Email Subject",
        received_at=datetime.utcnow(),
        status="pending",
    )
    async_db_session.add(email)
    await async_db_session.commit()
    await async_db_session.refresh(email)
    return email


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workflow_state_transitions(
    async_db_session, test_user, test_folders, test_email
):
    """Test workflow executes nodes in correct order.

    Verifies that the workflow:
    - Executes nodes sequentially: extract_context → classify → send_telegram → await_approval
    - Updates state after each node
    - Pauses at await_approval (no further execution)
    - Does NOT execute execute_action or send_confirmation nodes
    """
    # Setup mocked external APIs
    with patch("app.workflows.nodes.GmailClient") as MockGmail, \
         patch("app.core.llm_client.LLMClient.receive_completion") as mock_llm:

        # Mock Gmail API response
        mock_gmail_instance = AsyncMock()
        mock_gmail_instance.get_message_detail.return_value = {
            "sender": "sender@example.com",
            "subject": "Test Email Subject",
            "body": "This is a test email about project updates.",
            "received_at": "2025-11-07T10:00:00Z",
        }
        MockGmail.return_value = mock_gmail_instance

        # Mock Gemini LLM response
        mock_llm.return_value = {
            "suggested_folder": "Work",
            "reasoning": "Email discusses project updates",
            "priority_score": 70,
            "confidence": 0.90,
        }

        # Initialize workflow tracker
        database_url = os.getenv("DATABASE_URL")
        mock_gmail_client = mock_gmail_instance
        mock_llm_client = AsyncMock()
        mock_llm_client.receive_completion = mock_llm

        tracker = WorkflowInstanceTracker(
            db=async_db_session,
            gmail_client=mock_gmail_client,
            llm_client=mock_llm_client,
            database_url=database_url,
        )

        # Start workflow
        thread_id = await tracker.start_workflow(
            email_id=test_email.id,
            user_id=test_user.id,
        )

        # Verify thread_id format
        assert thread_id.startswith(f"email_{test_email.id}_")

        # Verify workflow paused at await_approval (status updated)
        await async_db_session.refresh(test_email)
        assert test_email.status == "awaiting_approval"

        # Verify classification results stored in database
        assert test_email.classification == "sort_only"
        assert test_email.classification_reasoning == "Email discusses project updates"
        assert test_email.priority_score == 70
        assert test_email.is_priority is True  # priority_score >= 70

        # Verify proposed_folder_id is set correctly
        work_folder = next(f for f in test_folders if f.name == "Work")
        assert test_email.proposed_folder_id == work_folder.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workflow_checkpoint_persistence(
    async_db_session, test_user, test_folders, test_email
):
    """Test PostgreSQL checkpoint persistence after classification.

    Verifies that:
    - Workflow state is persisted to PostgreSQL checkpoints table
    - Checkpoint contains serialized EmailWorkflowState
    - Thread_id is stored correctly for later resumption
    - Checkpoint can be queried and retrieved
    """
    # Setup mocked external APIs
    with patch("app.workflows.nodes.GmailClient") as MockGmail, \
         patch("app.core.llm_client.LLMClient.receive_completion") as mock_llm:

        # Mock Gmail API
        mock_gmail_instance = AsyncMock()
        mock_gmail_instance.get_message_detail.return_value = {
            "sender": "sender@example.com",
            "subject": "Test Email Subject",
            "body": "Test email content",
            "received_at": "2025-11-07T10:00:00Z",
        }
        MockGmail.return_value = mock_gmail_instance

        # Mock Gemini LLM
        mock_llm.return_value = {
            "suggested_folder": "Work",
            "reasoning": "Work-related email",
            "priority_score": 60,
            "confidence": 0.85,
        }

        # Initialize workflow tracker
        database_url = os.getenv("DATABASE_URL")
        tracker = WorkflowInstanceTracker(
            db=async_db_session,
            gmail_client=mock_gmail_instance,
            llm_client=AsyncMock(receive_completion=mock_llm),
            database_url=database_url,
        )

        # Start workflow
        thread_id = await tracker.start_workflow(
            email_id=test_email.id,
            user_id=test_user.id,
        )

        # Query PostgreSQL checkpoints table
        # Note: LangGraph creates checkpoints table automatically
        checkpoint_query = f"""
            SELECT thread_id, checkpoint_ns, checkpoint
            FROM checkpoints
            WHERE thread_id = '{thread_id}'
            ORDER BY checkpoint_id DESC
            LIMIT 1
        """
        result = await async_db_session.execute(checkpoint_query)
        checkpoint_row = result.fetchone()

        # Verify checkpoint exists
        assert checkpoint_row is not None, "Checkpoint not found in database"
        assert checkpoint_row[0] == thread_id

        # Verify checkpoint contains workflow state
        # Note: Checkpoint is stored as binary/JSON, exact format depends on LangGraph version
        # We verify it exists and has the correct thread_id
        assert checkpoint_row[1] is not None  # checkpoint_ns
        assert checkpoint_row[2] is not None  # checkpoint (serialized state)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_classification_result_stored_in_database(
    async_db_session, test_user, test_folders, test_email
):
    """Test classification results are stored in EmailProcessingQueue.

    Verifies that workflow correctly updates database with:
    - proposed_folder_id (lookup by folder name)
    - classification_reasoning
    - priority_score
    - is_priority flag
    - status = "awaiting_approval"
    """
    # Setup mocked external APIs
    with patch("app.workflows.nodes.GmailClient") as MockGmail, \
         patch("app.core.llm_client.LLMClient.receive_completion") as mock_llm:

        # Mock Gmail API
        mock_gmail_instance = AsyncMock()
        mock_gmail_instance.get_message_detail.return_value = {
            "sender": "sender@example.com",
            "subject": "Personal Email",
            "body": "Planning family vacation next month",
            "received_at": "2025-11-07T10:00:00Z",
        }
        MockGmail.return_value = mock_gmail_instance

        # Mock Gemini LLM to classify as Personal with high priority
        mock_llm.return_value = {
            "suggested_folder": "Personal",
            "reasoning": "Family vacation planning email",
            "priority_score": 85,
            "confidence": 0.92,
        }

        # Initialize workflow tracker
        database_url = os.getenv("DATABASE_URL")
        tracker = WorkflowInstanceTracker(
            db=async_db_session,
            gmail_client=mock_gmail_instance,
            llm_client=AsyncMock(receive_completion=mock_llm),
            database_url=database_url,
        )

        # Start workflow
        await tracker.start_workflow(
            email_id=test_email.id,
            user_id=test_user.id,
        )

        # Refresh email from database
        await async_db_session.refresh(test_email)

        # Verify all classification fields updated correctly
        personal_folder = next(f for f in test_folders if f.name == "Personal")
        assert test_email.proposed_folder_id == personal_folder.id
        assert test_email.classification_reasoning == "Family vacation planning email"
        assert test_email.priority_score == 85
        assert test_email.is_priority is True  # 85 >= 70
        assert test_email.status == "awaiting_approval"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workflow_error_handling(
    async_db_session, test_user, test_folders, test_email
):
    """Test workflow continues with fallback classification when Gemini fails.

    Verifies that:
    - Gemini API errors trigger fallback classification
    - Workflow continues (does not crash)
    - Email is classified as "Unclassified" folder
    - Email status is still "awaiting_approval" (workflow did not fail)
    """
    # Setup mocked external APIs
    with patch("app.workflows.nodes.GmailClient") as MockGmail, \
         patch("app.core.llm_client.LLMClient.receive_completion") as mock_llm:

        # Mock Gmail API (successful)
        mock_gmail_instance = AsyncMock()
        mock_gmail_instance.get_message_detail.return_value = {
            "sender": "sender@example.com",
            "subject": "Test Email",
            "body": "Test content",
            "received_at": "2025-11-07T10:00:00Z",
        }
        MockGmail.return_value = mock_gmail_instance

        # Mock Gemini LLM to raise API error
        mock_llm.side_effect = GeminiAPIError("Rate limit exceeded")

        # Initialize workflow tracker
        database_url = os.getenv("DATABASE_URL")
        tracker = WorkflowInstanceTracker(
            db=async_db_session,
            gmail_client=mock_gmail_instance,
            llm_client=AsyncMock(receive_completion=mock_llm),
            database_url=database_url,
        )

        # Start workflow (should NOT raise exception)
        thread_id = await tracker.start_workflow(
            email_id=test_email.id,
            user_id=test_user.id,
        )

        # Verify workflow completed with fallback classification
        await async_db_session.refresh(test_email)

        # Verify fallback classification applied
        unclassified_folder = next(f for f in test_folders if f.name == "Unclassified")
        assert test_email.proposed_folder_id == unclassified_folder.id
        assert "GeminiAPIError" in test_email.classification_reasoning
        assert test_email.priority_score == 50  # Medium priority for manual review
        assert test_email.is_priority is False  # 50 < 70
        assert test_email.status == "awaiting_approval"  # Workflow continued

        # Verify thread_id was generated
        assert thread_id is not None
        assert thread_id.startswith(f"email_{test_email.id}_")
