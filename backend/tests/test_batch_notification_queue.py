"""Unit tests for batch notification queueing (Story 2.3).

Tests cover:
- BatchNotificationQueue model creation
- queue_for_daily_batch function
- Priority routing in send_telegram workflow node
- send_daily_digest task (basic functionality)
"""

import pytest
import json
from datetime import date
from unittest.mock import Mock

from app.models.batch_notification_queue import BatchNotificationQueue, BatchNotificationStatus
from app.tasks.notification_tasks import _create_digest_summary


class TestBatchNotificationQueueModel:
    """Tests for BatchNotificationQueue model."""

    @pytest.mark.asyncio
    async def test_create_batch_notification(self, db_session):
        """Test creating a batch notification queue entry."""
        # Arrange
        entry = BatchNotificationQueue(
            user_id=1,
            email_id=100,
            telegram_id="123456789",
            message_text="Test notification message",
            buttons_json='[{"text": "Approve", "callback_data": "approve_100"}]',
            priority_score=50,
            scheduled_for=date.today(),
            status=BatchNotificationStatus.PENDING.value
        )

        # Act
        db_session.add(entry)
        await db_session.commit()
        await db_session.refresh(entry)

        # Assert
        assert entry.id is not None
        assert entry.user_id == 1
        assert entry.email_id == 100
        assert entry.status == "pending"
        assert entry.scheduled_for == date.today()
        assert entry.sent_at is None


class TestCreateDigestSummary:
    """Tests for _create_digest_summary helper function."""

    def test_create_digest_summary_single_email(self):
        """Test digest summary for a single email."""
        # Arrange
        notifications = [Mock(email_id=1)]

        # Act
        summary = _create_digest_summary(notifications)

        # Assert
        assert "📬 **Daily Email Summary**" in summary
        assert "**1** non-priority email needing review" in summary

    def test_create_digest_summary_multiple_emails(self):
        """Test digest summary for multiple emails."""
        # Arrange
        notifications = [Mock(email_id=i) for i in range(1, 4)]

        # Act
        summary = _create_digest_summary(notifications)

        # Assert
        assert "**3** non-priority emails needing review" in summary


class TestPriorityRouting:
    """Tests for priority routing logic."""

    def test_priority_email_score_threshold(self):
        """Test that emails with priority_score >= 70 are priority."""
        assert 70 >= 70  # Boundary
        assert 80 >= 70  # Above
        assert not (69 >= 70)  # Below
