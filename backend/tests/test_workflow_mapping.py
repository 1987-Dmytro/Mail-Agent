"""Unit tests for WorkflowMapping model."""

import pytest
from datetime import datetime, UTC
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.workflow_mapping import WorkflowMapping
from app.models.user import User
from app.models.email import EmailProcessingQueue


class TestWorkflowMappingModel:
    """Test cases for WorkflowMapping SQLModel."""

    @pytest.mark.asyncio
    async def test_create_workflow_mapping(self, db_session, test_user, test_email):
        """Test creating a WorkflowMapping entry."""
        thread_id = f"email_{test_email.id}_test-uuid-123"

        workflow_mapping = WorkflowMapping(
            email_id=test_email.id,
            user_id=test_user.id,
            thread_id=thread_id,
            telegram_message_id=None,
            workflow_state="initialized",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        db_session.add(workflow_mapping)
        await db_session.commit()
        await db_session.refresh(workflow_mapping)

        # Verify fields
        assert workflow_mapping.id is not None
        assert workflow_mapping.email_id == test_email.id
        assert workflow_mapping.user_id == test_user.id
        assert workflow_mapping.thread_id == thread_id
        assert workflow_mapping.telegram_message_id is None
        assert workflow_mapping.workflow_state == "initialized"
        assert workflow_mapping.created_at is not None
        assert workflow_mapping.updated_at is not None

    @pytest.mark.asyncio
    async def test_unique_constraint_on_email_id(self, db_session, test_user, test_email):
        """Test that email_id must be unique."""
        thread_id_1 = f"email_{test_email.id}_uuid-1"
        thread_id_2 = f"email_{test_email.id}_uuid-2"

        # Create first mapping
        mapping1 = WorkflowMapping(
            email_id=test_email.id,
            user_id=test_user.id,
            thread_id=thread_id_1,
            workflow_state="initialized",
        )
        db_session.add(mapping1)
        await db_session.commit()

        # Try to create second mapping with same email_id
        mapping2 = WorkflowMapping(
            email_id=test_email.id,  # Duplicate email_id
            user_id=test_user.id,
            thread_id=thread_id_2,  # Different thread_id
            workflow_state="initialized",
        )
        db_session.add(mapping2)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_unique_constraint_on_thread_id(self, db_session, test_user):
        """Test that thread_id must be unique."""
        # Create two emails
        email1 = EmailProcessingQueue(
            user_id=test_user.id,
            gmail_message_id="gmail_msg_1",
            gmail_thread_id="gmail_thread_1",
            sender="test1@example.com",
            subject="Test 1",
            received_at=datetime.now(UTC),
        )
        email2 = EmailProcessingQueue(
            user_id=test_user.id,
            gmail_message_id="gmail_msg_2",
            gmail_thread_id="gmail_thread_2",
            sender="test2@example.com",
            subject="Test 2",
            received_at=datetime.now(UTC),
        )
        db_session.add(email1)
        db_session.add(email2)
        await db_session.commit()
        await db_session.refresh(email1)
        await db_session.refresh(email2)

        thread_id = "email_123_shared-uuid"

        # Create first mapping
        mapping1 = WorkflowMapping(
            email_id=email1.id,
            user_id=test_user.id,
            thread_id=thread_id,
            workflow_state="initialized",
        )
        db_session.add(mapping1)
        await db_session.commit()

        # Try to create second mapping with same thread_id
        mapping2 = WorkflowMapping(
            email_id=email2.id,  # Different email_id
            user_id=test_user.id,
            thread_id=thread_id,  # Duplicate thread_id
            workflow_state="initialized",
        )
        db_session.add(mapping2)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_update_telegram_message_id(self, db_session, test_user, test_email):
        """Test updating telegram_message_id after message sent."""
        thread_id = f"email_{test_email.id}_test-uuid"

        # Create mapping without telegram_message_id
        mapping = WorkflowMapping(
            email_id=test_email.id,
            user_id=test_user.id,
            thread_id=thread_id,
            telegram_message_id=None,
            workflow_state="initialized",
        )
        db_session.add(mapping)
        await db_session.commit()
        await db_session.refresh(mapping)

        assert mapping.telegram_message_id is None

        # Update telegram_message_id (simulating send_telegram node)
        mapping.telegram_message_id = "12345"
        mapping.workflow_state = "awaiting_approval"
        await db_session.commit()
        await db_session.refresh(mapping)

        assert mapping.telegram_message_id == "12345"
        assert mapping.workflow_state == "awaiting_approval"

    @pytest.mark.asyncio
    async def test_cascade_delete_on_email_delete(self, db_session, test_user, test_email):
        """Test that WorkflowMapping is deleted when email is deleted."""
        thread_id = f"email_{test_email.id}_test-uuid"

        # Create mapping
        mapping = WorkflowMapping(
            email_id=test_email.id,
            user_id=test_user.id,
            thread_id=thread_id,
            workflow_state="initialized",
        )
        db_session.add(mapping)
        await db_session.commit()
        await db_session.refresh(mapping)

        mapping_id = mapping.id

        # Delete email
        await db_session.delete(test_email)
        await db_session.commit()

        # Verify mapping is also deleted (CASCADE)
        result = await db_session.execute(
            select(WorkflowMapping).where(WorkflowMapping.id == mapping_id)
        )
        deleted_mapping = result.scalar_one_or_none()
        assert deleted_mapping is None

    @pytest.mark.asyncio
    async def test_cascade_delete_on_user_delete(self, db_session):
        """Test that WorkflowMapping is deleted when user is deleted."""
        # Create user
        user = User(
            email="temp_user@example.com",
            is_active=True,
            onboarding_completed=False,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create email for user
        email = EmailProcessingQueue(
            user_id=user.id,
            gmail_message_id="temp_gmail_msg",
            gmail_thread_id="temp_gmail_thread",
            sender="temp@example.com",
            subject="Temp",
            received_at=datetime.now(UTC),
        )
        db_session.add(email)
        await db_session.commit()
        await db_session.refresh(email)

        # Create mapping
        thread_id = f"email_{email.id}_test-uuid"
        mapping = WorkflowMapping(
            email_id=email.id,
            user_id=user.id,
            thread_id=thread_id,
            workflow_state="initialized",
        )
        db_session.add(mapping)
        await db_session.commit()
        await db_session.refresh(mapping)

        mapping_id = mapping.id

        # Delete user (should cascade to email, then to mapping)
        await db_session.delete(user)
        await db_session.commit()

        # Verify mapping is also deleted (CASCADE via user)
        result = await db_session.execute(
            select(WorkflowMapping).where(WorkflowMapping.id == mapping_id)
        )
        deleted_mapping = result.scalar_one_or_none()
        assert deleted_mapping is None

    @pytest.mark.asyncio
    async def test_lookup_by_thread_id(self, db_session, test_user, test_email):
        """Test looking up WorkflowMapping by thread_id (for callback reconnection)."""
        thread_id = f"email_{test_email.id}_test-uuid"

        mapping = WorkflowMapping(
            email_id=test_email.id,
            user_id=test_user.id,
            thread_id=thread_id,
            workflow_state="initialized",
        )
        db_session.add(mapping)
        await db_session.commit()

        # Lookup by thread_id (simulating Telegram callback handler)
        result = await db_session.execute(
            select(WorkflowMapping).where(WorkflowMapping.thread_id == thread_id)
        )
        found_mapping = result.scalar_one_or_none()

        assert found_mapping is not None
        assert found_mapping.thread_id == thread_id
        assert found_mapping.email_id == test_email.id

    @pytest.mark.asyncio
    async def test_workflow_state_transitions(self, db_session, test_user, test_email):
        """Test workflow state transitions: initialized -> awaiting_approval -> completed."""
        thread_id = f"email_{test_email.id}_test-uuid"

        mapping = WorkflowMapping(
            email_id=test_email.id,
            user_id=test_user.id,
            thread_id=thread_id,
            workflow_state="initialized",
        )
        db_session.add(mapping)
        await db_session.commit()
        await db_session.refresh(mapping)

        # Transition to awaiting_approval
        mapping.workflow_state = "awaiting_approval"
        await db_session.commit()
        await db_session.refresh(mapping)
        assert mapping.workflow_state == "awaiting_approval"

        # Transition to completed
        mapping.workflow_state = "completed"
        await db_session.commit()
        await db_session.refresh(mapping)
        assert mapping.workflow_state == "completed"
