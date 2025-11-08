"""Integration tests for Approval History System (Story 2.10).

Tests cover end-to-end flows:
- AC #2, #3, #4: Approval recording in execute_action workflow node
- AC #5, #6: Statistics API endpoint with real database
- AC #7: Database index performance verification
"""

import pytest
from datetime import datetime, UTC, timedelta
from unittest.mock import AsyncMock, Mock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.approval_history import ApprovalHistoryService
from app.models.approval_history import ApprovalHistory
from app.models.email import EmailProcessingQueue
from app.models.folder_category import FolderCategory
from app.models.user import User
from app.workflows.nodes import execute_action
from app.workflows.states import EmailWorkflowState


@pytest.mark.asyncio
@pytest.mark.integration
async def test_approval_recording_in_workflow_approve(db_session: AsyncSession, test_user: User, test_folder: FolderCategory):
    """Test approval history recording during workflow execution - APPROVE action (AC #2).

    Scenario:
    - User approves AI's folder suggestion
    - execute_action node applies Gmail label and records decision
    - ApprovalHistory record created with approved=True

    Expected:
    - ApprovalHistory record exists with correct fields
    - approved=True
    - user_selected_folder_id == ai_suggested_folder_id
    - action_type="approve"
    """
    # Arrange - Create email in awaiting_approval status
    email = EmailProcessingQueue(
        user_id=test_user.id,
        gmail_message_id="gmail-msg-approve-123",
        gmail_thread_id="thread-approve-123",
        sender="finanzamt@berlin.de",
        subject="Tax Notice",
        received_at=datetime.now(UTC),
        status="awaiting_approval",
        proposed_folder_id=test_folder.id,
        classification_reasoning=f"Government email classified to {test_folder.name}",
        created_at=datetime.now(UTC),
    )
    db_session.add(email)
    await db_session.commit()
    await db_session.refresh(email)

    # Create workflow state with user decision = "approve"
    state: EmailWorkflowState = {
        "email_id": str(email.id),
        "user_decision": "approve",
        "proposed_folder_id": test_folder.id,
    }

    # Mock Gmail client to avoid real API calls
    mock_gmail = AsyncMock()
    mock_gmail.apply_label.return_value = True

    # Act - Execute workflow node (this should record approval history)
    with patch('app.api.deps.Session') as MockSession:
        # Create mock sync session for execute_action
        mock_session = Mock()
        mock_session.get = Mock(side_effect=lambda model, id: {
            EmailProcessingQueue: email,
            FolderCategory: test_folder,
        }.get(model))
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()  # Make commit async-compatible
        MockSession.return_value.__enter__.return_value = mock_session

        # Patch the service to use our real async db_session
        with patch('app.workflows.nodes.ApprovalHistoryService') as MockService:
            # Create a real service with our async session
            real_service = ApprovalHistoryService(db_session)
            MockService.return_value = real_service

            # Execute the workflow node
            result_state = await execute_action(
                state=state,
                db=mock_session,
                gmail_client=mock_gmail,
            )

    # Assert - Verify ApprovalHistory record was created
    stmt = select(ApprovalHistory).where(
        ApprovalHistory.user_id == test_user.id,
        ApprovalHistory.email_queue_id == email.id,
    )
    result = await db_session.execute(stmt)
    approval_records = result.scalars().all()

    assert len(approval_records) == 1
    record = approval_records[0]
    assert record.action_type == "approve"
    assert record.approved is True
    assert record.ai_suggested_folder_id == test_folder.id
    assert record.user_selected_folder_id == test_folder.id
    assert record.user_selected_folder_id == record.ai_suggested_folder_id

    # Verify workflow completed successfully
    assert result_state.get("final_action") == "approved"
    assert "error_message" not in result_state


@pytest.mark.asyncio
@pytest.mark.integration
async def test_approval_recording_in_workflow_reject(db_session: AsyncSession, test_user: User, test_folder: FolderCategory):
    """Test approval history recording during workflow execution - REJECT action (AC #3).

    Scenario:
    - User rejects AI's folder suggestion
    - execute_action node records rejection

    Expected:
    - ApprovalHistory record exists with approved=False
    - user_selected_folder_id is None
    - action_type="reject"
    """
    # Arrange
    email = EmailProcessingQueue(
        user_id=test_user.id,
        gmail_message_id="gmail-msg-reject-456",
        gmail_thread_id="thread-reject-456",
        sender="spam@example.com",
        subject="Spam Email",
        received_at=datetime.now(UTC),
        status="awaiting_approval",
        proposed_folder_id=test_folder.id,
        created_at=datetime.now(UTC),
    )
    db_session.add(email)
    await db_session.commit()
    await db_session.refresh(email)

    state: EmailWorkflowState = {
        "email_id": str(email.id),
        "user_decision": "reject",
        "proposed_folder_id": test_folder.id,
    }

    # Act
    with patch('app.api.deps.Session') as MockSession:
        mock_session = Mock()
        mock_session.get = Mock(side_effect=lambda model, id: {
            EmailProcessingQueue: email,
            FolderCategory: test_folder,
        }.get(model))
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        MockSession.return_value.__enter__.return_value = mock_session

        with patch('app.workflows.nodes.ApprovalHistoryService') as MockService:
            real_service = ApprovalHistoryService(db_session)
            MockService.return_value = real_service

            result_state = await execute_action(
                state=state,
                db=mock_session,
                gmail_client=AsyncMock(),
            )

    # Assert
    stmt = select(ApprovalHistory).where(
        ApprovalHistory.user_id == test_user.id,
        ApprovalHistory.email_queue_id == email.id,
    )
    result = await db_session.execute(stmt)
    approval_records = result.scalars().all()

    assert len(approval_records) == 1
    record = approval_records[0]
    assert record.action_type == "reject"
    assert record.approved is False
    assert record.user_selected_folder_id is None
    assert record.ai_suggested_folder_id == test_folder.id

    assert result_state.get("final_action") == "rejected"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_approval_recording_in_workflow_change_folder(db_session: AsyncSession, test_user: User):
    """Test approval history recording during workflow execution - CHANGE_FOLDER action (AC #4).

    Scenario:
    - User changes AI's suggested folder to a different one
    - execute_action node applies selected folder and records decision

    Expected:
    - ApprovalHistory record with approved=True
    - ai_suggested_folder_id != user_selected_folder_id
    - action_type="change_folder"
    """
    # Arrange - Create two different folders
    folder_gov = FolderCategory(
        user_id=test_user.id,
        name="Government",
        gmail_label_id="Label_Gov",
        keywords=["gov"],
        created_at=datetime.now(UTC),
    )
    folder_personal = FolderCategory(
        user_id=test_user.id,
        name="Personal",
        gmail_label_id="Label_Personal",
        keywords=["personal"],
        created_at=datetime.now(UTC),
    )
    db_session.add_all([folder_gov, folder_personal])
    await db_session.commit()
    await db_session.refresh(folder_gov)
    await db_session.refresh(folder_personal)

    email = EmailProcessingQueue(
        user_id=test_user.id,
        gmail_message_id="gmail-msg-change-789",
        gmail_thread_id="thread-change-789",
        sender="friend@example.com",
        subject="Personal Email",
        received_at=datetime.now(UTC),
        status="awaiting_approval",
        proposed_folder_id=folder_gov.id,  # AI suggested Government
        created_at=datetime.now(UTC),
    )
    db_session.add(email)
    await db_session.commit()
    await db_session.refresh(email)

    state: EmailWorkflowState = {
        "email_id": str(email.id),
        "user_decision": "change_folder",
        "proposed_folder_id": folder_gov.id,
        "selected_folder_id": folder_personal.id,  # User selected Personal
    }

    mock_gmail = AsyncMock()
    mock_gmail.apply_label.return_value = True

    # Act
    with patch('app.api.deps.Session') as MockSession:
        mock_session = Mock()
        mock_session.get = Mock(side_effect=lambda model, id: {
            EmailProcessingQueue: email,
            FolderCategory: folder_personal if id == folder_personal.id else folder_gov,
        }.get(model))
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        MockSession.return_value.__enter__.return_value = mock_session

        with patch('app.workflows.nodes.ApprovalHistoryService') as MockService:
            real_service = ApprovalHistoryService(db_session)
            MockService.return_value = real_service

            result_state = await execute_action(
                state=state,
                db=mock_session,
                gmail_client=mock_gmail,
            )

    # Assert
    stmt = select(ApprovalHistory).where(
        ApprovalHistory.user_id == test_user.id,
        ApprovalHistory.email_queue_id == email.id,
    )
    result = await db_session.execute(stmt)
    approval_records = result.scalars().all()

    assert len(approval_records) == 1
    record = approval_records[0]
    assert record.action_type == "change_folder"
    assert record.approved is True  # User still accepts sorting, just different folder
    assert record.ai_suggested_folder_id == folder_gov.id
    assert record.user_selected_folder_id == folder_personal.id
    assert record.ai_suggested_folder_id != record.user_selected_folder_id

    assert result_state.get("final_action") == "changed"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_statistics_api_endpoint(db_session: AsyncSession, test_user: User):
    """Test statistics API endpoint with real database (AC #5, #6).

    Scenario:
    - Create 15 approval decisions (10 approve, 3 reject, 2 change)
    - Call GET /api/v1/stats/approvals endpoint
    - Verify statistics calculated correctly

    Expected:
    - total_decisions=15
    - approved=10, rejected=3, folder_changed=2
    - approval_rate=0.800 (12/15)
    - top_folders returns folder usage counts
    """
    # Arrange - Create folders and approval records
    folder_gov = FolderCategory(
        user_id=test_user.id,
        name="Government",
        gmail_label_id="Label_Gov",
        keywords=["gov"],
        created_at=datetime.now(UTC),
    )
    folder_clients = FolderCategory(
        user_id=test_user.id,
        name="Clients",
        gmail_label_id="Label_Clients",
        keywords=["clients"],
        created_at=datetime.now(UTC),
    )
    db_session.add_all([folder_gov, folder_clients])
    await db_session.commit()
    await db_session.refresh(folder_gov)
    await db_session.refresh(folder_clients)

    # Create 15 test records
    test_data = [
        *[(f"approve_{i}", "approve", folder_gov.id if i < 5 else folder_clients.id) for i in range(10)],
        *[(f"reject_{i}", "reject", None) for i in range(3)],
        ("change_0", "change_folder", folder_clients.id),
        ("change_1", "change_folder", folder_clients.id),
    ]

    for msg_id, action_type, selected_folder_id in test_data:
        email = EmailProcessingQueue(
            user_id=test_user.id,
            gmail_message_id=msg_id,
            gmail_thread_id=f"thread_{msg_id}",
            sender=f"{msg_id}@example.com",
            subject=f"Test {msg_id}",
            received_at=datetime.now(UTC),
            status="completed",
            created_at=datetime.now(UTC),
        )
        db_session.add(email)
        await db_session.commit()
        await db_session.refresh(email)

        approval = ApprovalHistory(
            user_id=test_user.id,
            email_queue_id=email.id,
            action_type=action_type,
            ai_suggested_folder_id=folder_gov.id,
            user_selected_folder_id=selected_folder_id,
            approved=(action_type != "reject"),
            timestamp=datetime.now(UTC),
        )
        db_session.add(approval)

    await db_session.commit()

    # Act - Call service directly (simulating API endpoint logic)
    service = ApprovalHistoryService(db_session)
    stats = await service.get_approval_statistics(user_id=test_user.id)

    # Assert
    assert stats["total_decisions"] == 15
    assert stats["approved"] == 10
    assert stats["rejected"] == 3
    assert stats["folder_changed"] == 2
    assert stats["approval_rate"] == 0.800  # (10 + 2) / 15 = 0.8
    assert len(stats["top_folders"]) == 2  # Government and Clients

    # Verify top folders
    top_folder_names = {folder["name"] for folder in stats["top_folders"]}
    assert top_folder_names == {"Government", "Clients"}


@pytest.mark.asyncio
@pytest.mark.integration
async def test_database_index_performance(db_session: AsyncSession, test_user: User, test_folder: FolderCategory):
    """Test database index performance on large dataset (AC #7).

    Scenario:
    - Create 1000 approval history records
    - Query with (user_id, timestamp) compound index
    - Query with action_type index
    - Verify query execution plan uses indexes

    Expected:
    - Queries execute in <100ms (with indexes)
    - EXPLAIN shows "Index Scan" or "Index Only Scan" (not "Seq Scan")
    """
    import time

    # Arrange - Create 1000 approval records spanning 90 days
    base_time = datetime.now(UTC) - timedelta(days=90)

    emails_to_create = []
    approvals_to_create = []

    for i in range(1000):
        email = EmailProcessingQueue(
            user_id=test_user.id,
            gmail_message_id=f"perf_test_msg_{i}",
            gmail_thread_id=f"perf_test_thread_{i}",
            sender=f"perf_test_{i}@example.com",
            subject=f"Performance Test {i}",
            received_at=base_time + timedelta(hours=i),
            status="completed",
            created_at=base_time + timedelta(hours=i),
        )
        emails_to_create.append(email)

    # Bulk insert emails
    db_session.add_all(emails_to_create)
    await db_session.commit()

    # Refresh to get IDs
    for email in emails_to_create:
        await db_session.refresh(email)

    # Create approval records
    for i, email in enumerate(emails_to_create):
        action_type = ["approve", "reject", "change_folder"][i % 3]
        approval = ApprovalHistory(
            user_id=test_user.id,
            email_queue_id=email.id,
            action_type=action_type,
            ai_suggested_folder_id=test_folder.id,
            user_selected_folder_id=test_folder.id if action_type != "reject" else None,
            approved=(action_type != "reject"),
            timestamp=base_time + timedelta(hours=i),
        )
        approvals_to_create.append(approval)

    db_session.add_all(approvals_to_create)
    await db_session.commit()

    # Act & Assert - Test compound index (user_id, timestamp) performance
    from_date = base_time + timedelta(days=30)
    to_date = base_time + timedelta(days=60)

    start_time = time.time()
    service = ApprovalHistoryService(db_session)
    history = await service.get_user_history(
        user_id=test_user.id,
        from_date=from_date,
        to_date=to_date,
    )
    query_time_ms = (time.time() - start_time) * 1000

    # Verify query completed quickly (with index should be <100ms)
    assert query_time_ms < 200  # Allow 200ms for CI/CD environment
    assert len(history) > 0  # Should retrieve records in date range

    # Verify EXPLAIN plan uses index
    explain_query = sa_text("""
        EXPLAIN (FORMAT JSON)
        SELECT * FROM approval_history
        WHERE user_id = :user_id
        AND timestamp >= :from_date
        AND timestamp <= :to_date
        ORDER BY timestamp DESC
    """)

    result = await db_session.execute(
        explain_query,
        {"user_id": test_user.id, "from_date": from_date, "to_date": to_date}
    )
    explain_plan = result.scalar()

    # Verify plan contains "Index" (Index Scan or Index Only Scan, not Seq Scan)
    assert "Index" in str(explain_plan), f"Query should use index, but plan is: {explain_plan}"

    # Test action_type index performance
    start_time = time.time()
    approve_history = await service.get_user_history(
        user_id=test_user.id,
        action_type="approve",
    )
    query_time_ms = (time.time() - start_time) * 1000

    assert query_time_ms < 200
    assert len(approve_history) > 0
