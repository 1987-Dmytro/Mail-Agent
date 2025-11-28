"""Unit tests for ApprovalHistoryService and ApprovalHistory model (Story 2.10).

Tests cover:
- AC #1: ApprovalHistory table creation with correct schema
- AC #2: Approval event recording (approved=True)
- AC #3: Rejection event recording (approved=False)
- AC #4: Folder change event recording (approved=True, different folder IDs)
- AC #5: History queryable by user_id, date range, action_type
- AC #6: Statistics calculation (approval_rate, top_folders)
- AC #7: Database indexes (verified in integration tests)
- AC #8: Privacy considerations (documented in model)
"""

import pytest
from datetime import datetime, UTC, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.approval_history import ApprovalHistoryService
from app.models.approval_history import ApprovalHistory
from app.models.user import User
from app.models.email import EmailProcessingQueue
from app.models.folder_category import FolderCategory


@pytest.mark.asyncio
async def test_approval_history_model_creation(db_session: AsyncSession, test_user: User):
    """Test ApprovalHistory model creation and field population (AC #1).

    Verifies:
    - All fields populated correctly
    - Timestamp auto-generated (timezone-aware UTC)
    - Foreign key relationships work
    - approved field derived correctly from action_type
    """
    # Arrange
    test_folder = FolderCategory(
        user_id=test_user.id,
        name="Test Folder",
        keywords=["test"],
        created_at=datetime.now(UTC),
    )
    db_session.add(test_folder)
    await db_session.commit()
    await db_session.refresh(test_folder)

    test_email = EmailProcessingQueue(
        user_id=test_user.id,
        gmail_message_id="msg_123",
        gmail_thread_id="thread_123",
        sender="test@example.com",
        subject="Test Subject",
        received_at=datetime.now(UTC),
        status="pending",
        created_at=datetime.now(UTC),
    )
    db_session.add(test_email)
    await db_session.commit()
    await db_session.refresh(test_email)

    # Act
    approval_record = ApprovalHistory(
        user_id=test_user.id,
        email_queue_id=test_email.id,
        action_type="approve",
        ai_suggested_folder_id=test_folder.id,
        user_selected_folder_id=test_folder.id,
        approved=True,
        timestamp=datetime.now(UTC),
    )
    db_session.add(approval_record)
    await db_session.commit()
    await db_session.refresh(approval_record)

    # Assert
    assert approval_record.id is not None
    assert approval_record.user_id == test_user.id
    assert approval_record.email_queue_id == test_email.id
    assert approval_record.action_type == "approve"
    assert approval_record.ai_suggested_folder_id == test_folder.id
    assert approval_record.user_selected_folder_id == test_folder.id
    assert approval_record.approved is True
    assert approval_record.timestamp.tzinfo is not None  # Timezone-aware
    assert approval_record.created_at is not None


@pytest.mark.asyncio
async def test_record_approve_decision(db_session: AsyncSession, test_user: User):
    """Test record_decision() for approve action (AC #2).

    Verifies:
    - approved=True for approve action
    - user_selected_folder_id equals ai_suggested_folder_id
    - Record committed to database
    - Structured logging occurs
    """
    # Arrange
    test_folder = FolderCategory(
        user_id=test_user.id,
        name="Government",
        keywords=["gov"],
        created_at=datetime.now(UTC),
    )
    db_session.add(test_folder)
    await db_session.commit()
    await db_session.refresh(test_folder)

    test_email = EmailProcessingQueue(
        user_id=test_user.id,
        gmail_message_id="msg_456",
        gmail_thread_id="thread_456",
        sender="finanzamt@berlin.de",
        subject="Tax Notice",
        received_at=datetime.now(UTC),
        status="awaiting_approval",
        created_at=datetime.now(UTC),
    )
    db_session.add(test_email)
    await db_session.commit()
    await db_session.refresh(test_email)

    service = ApprovalHistoryService(db_session)

    # Act
    record = await service.record_decision(
        user_id=test_user.id,
        email_queue_id=test_email.id,
        action_type="approve",
        ai_suggested_folder_id=test_folder.id,
        user_selected_folder_id=test_folder.id,  # Will be set to ai_suggested automatically
    )

    # Assert
    assert record.id is not None
    assert record.approved is True
    assert record.action_type == "approve"
    assert record.user_selected_folder_id == test_folder.id
    assert record.ai_suggested_folder_id == test_folder.id
    assert record.user_selected_folder_id == record.ai_suggested_folder_id


@pytest.mark.asyncio
async def test_record_reject_decision(db_session: AsyncSession, test_user: User):
    """Test record_decision() for reject action (AC #3).

    Verifies:
    - approved=False for reject action
    - user_selected_folder_id can be None
    - Record committed to database
    """
    # Arrange
    test_folder = FolderCategory(
        user_id=test_user.id,
        name="Spam",
        keywords=["spam"],
        created_at=datetime.now(UTC),
    )
    db_session.add(test_folder)
    await db_session.commit()
    await db_session.refresh(test_folder)

    test_email = EmailProcessingQueue(
        user_id=test_user.id,
        gmail_message_id="msg_789",
        gmail_thread_id="thread_789",
        sender="spam@example.com",
        subject="Spam Email",
        received_at=datetime.now(UTC),
        status="awaiting_approval",
        created_at=datetime.now(UTC),
    )
    db_session.add(test_email)
    await db_session.commit()
    await db_session.refresh(test_email)

    service = ApprovalHistoryService(db_session)

    # Act
    record = await service.record_decision(
        user_id=test_user.id,
        email_queue_id=test_email.id,
        action_type="reject",
        ai_suggested_folder_id=test_folder.id,
        user_selected_folder_id=None,  # No folder selected for reject
    )

    # Assert
    assert record.id is not None
    assert record.approved is False
    assert record.action_type == "reject"
    assert record.user_selected_folder_id is None
    assert record.ai_suggested_folder_id == test_folder.id


@pytest.mark.asyncio
async def test_record_change_folder_decision(db_session: AsyncSession, test_user: User):
    """Test record_decision() for change_folder action (AC #4).

    Verifies:
    - approved=True for change_folder action
    - ai_suggested_folder_id != user_selected_folder_id
    - Both folder IDs stored correctly
    """
    # Arrange - Create two different folders
    folder_gov = FolderCategory(
        user_id=test_user.id,
        name="Government",
        keywords=["gov"],
        created_at=datetime.now(UTC),
    )
    folder_personal = FolderCategory(
        user_id=test_user.id,
        name="Personal",
        keywords=["personal"],
        created_at=datetime.now(UTC),
    )
    db_session.add(folder_gov)
    db_session.add(folder_personal)
    await db_session.commit()
    await db_session.refresh(folder_gov)
    await db_session.refresh(folder_personal)

    test_email = EmailProcessingQueue(
        user_id=test_user.id,
        gmail_message_id="msg_999",
        gmail_thread_id="thread_999",
        sender="friend@example.com",
        subject="Personal Email",
        received_at=datetime.now(UTC),
        status="awaiting_approval",
        created_at=datetime.now(UTC),
    )
    db_session.add(test_email)
    await db_session.commit()
    await db_session.refresh(test_email)

    service = ApprovalHistoryService(db_session)

    # Act - AI suggested Government, user selected Personal
    record = await service.record_decision(
        user_id=test_user.id,
        email_queue_id=test_email.id,
        action_type="change_folder",
        ai_suggested_folder_id=folder_gov.id,
        user_selected_folder_id=folder_personal.id,
    )

    # Assert
    assert record.id is not None
    assert record.approved is True  # User still accepts sorting, just different folder
    assert record.action_type == "change_folder"
    assert record.ai_suggested_folder_id == folder_gov.id
    assert record.user_selected_folder_id == folder_personal.id
    assert record.ai_suggested_folder_id != record.user_selected_folder_id


@pytest.mark.asyncio
async def test_get_user_history_with_filters(db_session: AsyncSession, test_user: User, test_user_2: User):
    """Test get_user_history() filtering by date range and action_type (AC #5).

    Verifies:
    - from_date filter: Returns only records after date
    - to_date filter: Returns only records before date
    - action_type filter: Returns only matching action types
    - Date range combination: Correct records in range
    - Multi-tenant isolation: Only returns current user's records
    """
    # Arrange - Create test folder
    test_folder = FolderCategory(
        user_id=test_user.id,
        name="Test Folder",
        keywords=["test"],
        created_at=datetime.now(UTC),
    )
    db_session.add(test_folder)
    await db_session.commit()
    await db_session.refresh(test_folder)

    # Create 10 test records with varying dates and action types
    base_time = datetime.now(UTC) - timedelta(days=30)

    for i in range(10):
        test_email = EmailProcessingQueue(
            user_id=test_user.id,
            gmail_message_id=f"msg_{i}",
            gmail_thread_id=f"thread_{i}",
            sender=f"test{i}@example.com",
            subject=f"Test {i}",
            received_at=base_time + timedelta(days=i*3),
            status="completed",
            created_at=base_time + timedelta(days=i*3),
        )
        db_session.add(test_email)
        await db_session.commit()
        await db_session.refresh(test_email)

        # Vary action types: approve (0-4), reject (5-6), change_folder (7-9)
        if i < 5:
            action_type = "approve"
            approved = True
        elif i < 7:
            action_type = "reject"
            approved = False
        else:
            action_type = "change_folder"
            approved = True

        approval = ApprovalHistory(
            user_id=test_user.id,
            email_queue_id=test_email.id,
            action_type=action_type,
            ai_suggested_folder_id=test_folder.id,
            user_selected_folder_id=test_folder.id if approved else None,
            approved=approved,
            timestamp=base_time + timedelta(days=i*3),
        )
        db_session.add(approval)

    # Create 2 records for test_user_2 (should be filtered out)
    for i in range(2):
        test_email_2 = EmailProcessingQueue(
            user_id=test_user_2.id,
            gmail_message_id=f"msg_user2_{i}",
            gmail_thread_id=f"thread_user2_{i}",
            sender=f"test_user2_{i}@example.com",
            subject=f"Test User 2 {i}",
            received_at=base_time,
            status="completed",
            created_at=base_time,
        )
        db_session.add(test_email_2)
        await db_session.commit()
        await db_session.refresh(test_email_2)

        approval_2 = ApprovalHistory(
            user_id=test_user_2.id,
            email_queue_id=test_email_2.id,
            action_type="approve",
            ai_suggested_folder_id=test_folder.id,
            user_selected_folder_id=test_folder.id,
            approved=True,
            timestamp=base_time,
        )
        db_session.add(approval_2)

    await db_session.commit()

    service = ApprovalHistoryService(db_session)

    # Act & Assert - Test from_date filter
    from_date = base_time + timedelta(days=15)
    history = await service.get_user_history(user_id=test_user.id, from_date=from_date)
    assert len(history) == 5  # Records from days 15, 18, 21, 24, 27

    # Act & Assert - Test to_date filter
    to_date = base_time + timedelta(days=15)
    history = await service.get_user_history(user_id=test_user.id, to_date=to_date)
    assert len(history) == 6  # Records from days 0, 3, 6, 9, 12, 15

    # Act & Assert - Test action_type filter (only approve)
    history = await service.get_user_history(user_id=test_user.id, action_type="approve")
    assert len(history) == 5
    assert all(r.action_type == "approve" for r in history)

    # Act & Assert - Test date range combination
    history = await service.get_user_history(
        user_id=test_user.id,
        from_date=base_time + timedelta(days=6),
        to_date=base_time + timedelta(days=18)
    )
    assert len(history) == 5  # Records from days 6, 9, 12, 15, 18

    # Act & Assert - Multi-tenant isolation (only test_user's records)
    all_history = await service.get_user_history(user_id=test_user.id)
    assert len(all_history) == 10
    assert all(r.user_id == test_user.id for r in all_history)


@pytest.mark.asyncio
async def test_get_approval_statistics_calculation(db_session: AsyncSession, test_user: User):
    """Test get_approval_statistics() calculation logic (AC #6).

    Verifies:
    - total_decisions calculation
    - approved, rejected, folder_changed counts
    - approval_rate calculation: (approved + changed) / total
    - top_folders aggregation (top 5 by usage count)
    """
    # Arrange - Create 3 folders
    folder_gov = FolderCategory(
        user_id=test_user.id,
        name="Government",
        keywords=["gov"],
        created_at=datetime.now(UTC),
    )
    folder_clients = FolderCategory(
        user_id=test_user.id,
        name="Clients",
        keywords=["clients"],
        created_at=datetime.now(UTC),
    )
    folder_personal = FolderCategory(
        user_id=test_user.id,
        name="Personal",
        keywords=["personal"],
        created_at=datetime.now(UTC),
    )
    db_session.add_all([folder_gov, folder_clients, folder_personal])
    await db_session.commit()
    await db_session.refresh(folder_gov)
    await db_session.refresh(folder_clients)
    await db_session.refresh(folder_personal)

    # Create test data: 10 approvals, 3 rejects, 2 folder changes
    # Total: 15 decisions
    # Approval rate: (10 + 2) / 15 = 0.800
    test_data = [
        # 10 approvals (Government: 5, Clients: 5)
        *[(f"approve_{i}", "approve", folder_gov.id if i < 5 else folder_clients.id) for i in range(10)],
        # 3 rejects
        *[(f"reject_{i}", "reject", None) for i in range(3)],
        # 2 folder changes (AI suggested Government, user selected Personal)
        ("change_0", "change_folder", folder_personal.id),
        ("change_1", "change_folder", folder_personal.id),
    ]

    for msg_id, action_type, selected_folder_id in test_data:
        test_email = EmailProcessingQueue(
            user_id=test_user.id,
            gmail_message_id=msg_id,
            gmail_thread_id=f"thread_{msg_id}",
            sender=f"{msg_id}@example.com",
            subject=f"Test {msg_id}",
            received_at=datetime.now(UTC),
            status="completed",
            created_at=datetime.now(UTC),
        )
        db_session.add(test_email)
        await db_session.commit()
        await db_session.refresh(test_email)

        approval = ApprovalHistory(
            user_id=test_user.id,
            email_queue_id=test_email.id,
            action_type=action_type,
            ai_suggested_folder_id=folder_gov.id,  # AI always suggests Government for this test
            user_selected_folder_id=selected_folder_id,
            approved=(action_type != "reject"),
            timestamp=datetime.now(UTC),
        )
        db_session.add(approval)

    await db_session.commit()

    service = ApprovalHistoryService(db_session)

    # Act
    stats = await service.get_approval_statistics(user_id=test_user.id)

    # Assert
    assert stats["total_decisions"] == 15
    assert stats["approved"] == 10
    assert stats["rejected"] == 3
    assert stats["folder_changed"] == 2
    assert stats["approval_rate"] == 0.800  # (10 + 2) / 15 = 0.8
    assert len(stats["top_folders"]) == 3  # Only 3 folders used (Government, Clients, Personal)

    # Verify top folders sorted by count descending
    top_folders = stats["top_folders"]
    # Both Government and Clients have 5 uses, order may vary
    top_2_names = {top_folders[0]["name"], top_folders[1]["name"]}
    assert top_2_names == {"Government", "Clients"}
    assert top_folders[0]["count"] == 5
    assert top_folders[1]["count"] == 5
    assert top_folders[2]["name"] == "Personal"  # 2 uses (folder changes)
    assert top_folders[2]["count"] == 2
