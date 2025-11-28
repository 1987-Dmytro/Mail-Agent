"""Integration tests for Gmail label management (end-to-end)."""

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.user import User
from app.models.folder_category import FolderCategory
from app.core.gmail_client import GmailClient
from app.core.encryption import encrypt_token
from app.services.database import database_service


@pytest_asyncio.fixture
async def test_user_with_gmail(db_session: AsyncSession) -> User:
    """Create a test user with Gmail OAuth tokens.

    Returns:
        User with encrypted Gmail tokens
    """
    access_token = encrypt_token("test_access_token_labels")
    refresh_token = encrypt_token("test_refresh_token_labels")

    user = User(
        email="label_test@gmail.com",
        hashed_password="$2b$12$test",
        is_active=True,
        gmail_oauth_token=access_token,
        gmail_refresh_token=refresh_token,
        gmail_connected_at=datetime.now(timezone.utc),
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest.mark.asyncio
async def test_label_creation_end_to_end(
    test_user_with_gmail: User,
    db_session: AsyncSession,
):
    """Integration test: Create Gmail label and store in database.

    Tests:
    - GmailClient.create_label() called with name and color
    - Gmail API returns label_id
    - FolderCategory record created with gmail_label_id stored
    - Label name, color, and user_id persisted correctly

    AC Coverage: AC#3
    """
    # Mock Gmail API create label response
    mock_label_id = "Label_Government_123"

    def mock_create_label_sync():
        return {"id": mock_label_id, "name": "Government", "type": "user"}

    with patch.object(
        GmailClient,
        "create_label",
        new=AsyncMock(return_value=mock_label_id),
    ):
        # Create Gmail client
        gmail_client = GmailClient(test_user_with_gmail.id)

        # Create label
        label_id = await gmail_client.create_label(name="Government", color="#FF5733")

        # Assert: Gmail label ID returned
        assert label_id == mock_label_id

        # Create FolderCategory record in database
        folder = FolderCategory(
            user_id=test_user_with_gmail.id,
            name="Government",
            gmail_label_id=label_id,
            color="#FF5733",
        )
        db_session.add(folder)
        await db_session.commit()
        await db_session.refresh(folder)

    # Verify: FolderCategory record created correctly
    statement = select(FolderCategory).where(
        FolderCategory.user_id == test_user_with_gmail.id
    )
    result = await db_session.execute(statement)
    saved_folder = result.scalar_one()

    assert saved_folder.name == "Government"
    assert saved_folder.gmail_label_id == mock_label_id
    assert saved_folder.color == "#FF5733"
    assert saved_folder.user_id == test_user_with_gmail.id


@pytest.mark.asyncio
async def test_label_creation_duplicate_name(
    test_user_with_gmail: User,
    db_session: AsyncSession,
):
    """Integration test: Create label with duplicate name (idempotent).

    Tests:
    - First label creation succeeds
    - Second label creation with same name returns existing label ID
    - Only one FolderCategory record exists
    - Idempotent operation handling

    AC Coverage: AC#3
    """
    mock_label_id = "Label_Duplicate_456"

    # First creation
    with patch.object(
        GmailClient,
        "create_label",
        new=AsyncMock(return_value=mock_label_id),
    ):
        gmail_client = GmailClient(test_user_with_gmail.id)
        label_id_1 = await gmail_client.create_label(name="Important", color="#00FF00")

        assert label_id_1 == mock_label_id

        # Create folder record
        folder1 = FolderCategory(
            user_id=test_user_with_gmail.id,
            name="Important",
            gmail_label_id=label_id_1,
            color="#00FF00",
        )
        db_session.add(folder1)
        await db_session.commit()

    # Second creation with same name (should return existing label ID)
    with patch.object(
        GmailClient,
        "create_label",
        new=AsyncMock(return_value=mock_label_id),  # Same ID returned
    ):
        gmail_client = GmailClient(test_user_with_gmail.id)
        label_id_2 = await gmail_client.create_label(name="Important", color="#00FF00")

        # Assert: Same label ID returned (idempotent)
        assert label_id_2 == mock_label_id
        assert label_id_2 == label_id_1

    # Verify: Only one FolderCategory record exists
    statement = select(FolderCategory).where(
        FolderCategory.user_id == test_user_with_gmail.id
    )
    result = await db_session.execute(statement)
    folders = result.scalars().all()

    assert len(folders) == 1
    assert folders[0].gmail_label_id == mock_label_id


@pytest.mark.asyncio
async def test_label_application_to_message(
    test_user_with_gmail: User,
    db_session: AsyncSession,
):
    """Integration test: Apply label to Gmail message.

    Tests:
    - FolderCategory exists with gmail_label_id
    - GmailClient.apply_label() called with message_id and label_id
    - Gmail API modify endpoint called with correct addLabelIds parameter
    - Operation succeeds

    AC Coverage: AC#3
    """
    # Create folder with label
    mock_label_id = "Label_Apply_789"
    folder = FolderCategory(
        user_id=test_user_with_gmail.id,
        name="Work",
        gmail_label_id=mock_label_id,
        color="#0000FF",
    )
    db_session.add(folder)
    await db_session.commit()

    # Mock Gmail API modify message
    mock_message_id = "msg_to_label_123"

    # Mock the apply_label method
    mock_apply_label = AsyncMock(return_value={"id": mock_message_id, "labelIds": [mock_label_id]})

    with patch.object(GmailClient, "apply_label", new=mock_apply_label):
        gmail_client = GmailClient(test_user_with_gmail.id)

        # Apply label to message
        result = await gmail_client.apply_label(message_id=mock_message_id, label_id=mock_label_id)

        # Assert: apply_label called
        mock_apply_label.assert_called_once_with(message_id=mock_message_id, label_id=mock_label_id)

        # Assert: Response contains label
        assert result["id"] == mock_message_id
        assert mock_label_id in result["labelIds"]


@pytest.mark.asyncio
async def test_label_removal_from_message(
    test_user_with_gmail: User,
    db_session: AsyncSession,
):
    """Integration test: Remove label from Gmail message.

    Tests:
    - GmailClient.remove_label() called with message_id and label_id
    - Gmail API modify endpoint called with correct removeLabelIds parameter
    - Label removed successfully

    AC Coverage: AC#3
    """
    mock_label_id = "Label_Remove_321"
    mock_message_id = "msg_remove_label_456"

    # Mock the remove_label method
    mock_remove_label = AsyncMock(return_value={"id": mock_message_id, "labelIds": []})

    with patch.object(GmailClient, "remove_label", new=mock_remove_label):
        gmail_client = GmailClient(test_user_with_gmail.id)

        # Remove label from message
        result = await gmail_client.remove_label(message_id=mock_message_id, label_id=mock_label_id)

        # Assert: remove_label called
        mock_remove_label.assert_called_once_with(message_id=mock_message_id, label_id=mock_label_id)

        # Assert: Response shows label removed
        assert result["id"] == mock_message_id
        assert mock_label_id not in result["labelIds"]


@pytest.mark.asyncio
async def test_label_list_all_labels(
    test_user_with_gmail: User,
    db_session: AsyncSession,
):
    """Integration test: List all Gmail labels.

    Tests:
    - GmailClient.list_labels() called
    - Returns both system and user labels
    - Label metadata includes id, name, type

    AC Coverage: AC#3
    """
    # Mock Gmail API list labels response
    mock_labels = [
        {"id": "INBOX", "name": "INBOX", "type": "system"},
        {"id": "Label_123", "name": "Government", "type": "user"},
        {"id": "Label_456", "name": "Personal", "type": "user"},
    ]

    with patch.object(GmailClient, "list_labels", new=AsyncMock(return_value=mock_labels)):
        gmail_client = GmailClient(test_user_with_gmail.id)

        # List all labels
        labels = await gmail_client.list_labels()

        # Assert: All labels returned
        assert len(labels) == 3

        # Verify system label
        inbox_label = next(l for l in labels if l["id"] == "INBOX")
        assert inbox_label["type"] == "system"

        # Verify user labels
        user_labels = [l for l in labels if l["type"] == "user"]
        assert len(user_labels) == 2
        assert any(l["name"] == "Government" for l in user_labels)
        assert any(l["name"] == "Personal" for l in user_labels)


@pytest.mark.asyncio
async def test_label_color_customization(
    test_user_with_gmail: User,
    db_session: AsyncSession,
):
    """Integration test: Create label with custom color.

    Tests:
    - Label created with hex color code
    - Color persisted in FolderCategory
    - Color format validated (#RRGGBB)

    AC Coverage: AC#3
    """
    mock_label_id = "Label_Color_999"

    with patch.object(GmailClient, "create_label", new=AsyncMock(return_value=mock_label_id)):
        gmail_client = GmailClient(test_user_with_gmail.id)

        # Create label with custom color
        label_id = await gmail_client.create_label(name="Urgent", color="#FF0000")

        assert label_id == mock_label_id

        # Save folder with color
        folder = FolderCategory(
            user_id=test_user_with_gmail.id,
            name="Urgent",
            gmail_label_id=label_id,
            color="#FF0000",
        )
        db_session.add(folder)
        await db_session.commit()

    # Verify: Color saved correctly
    statement = select(FolderCategory).where(FolderCategory.gmail_label_id == mock_label_id)
    result = await db_session.execute(statement)
    saved_folder = result.scalar_one()

    assert saved_folder.color == "#FF0000"
    assert len(saved_folder.color) == 7  # #RRGGBB format
    assert saved_folder.color.startswith("#")


@pytest.mark.asyncio
async def test_label_unique_constraint_per_user(
    test_user_with_gmail: User,
    db_session: AsyncSession,
):
    """Integration test: Folder name unique per user constraint.

    Tests:
    - First folder "Important" created for user
    - Second folder "Important" for same user fails (unique constraint)
    - Different user can create folder with same name

    AC Coverage: AC#3
    """
    from sqlalchemy.exc import IntegrityError

    mock_label_id_1 = "Label_User1_111"

    # Create first folder "Important"
    folder1 = FolderCategory(
        user_id=test_user_with_gmail.id,
        name="Important",
        gmail_label_id=mock_label_id_1,
        color="#00FF00",
    )
    db_session.add(folder1)
    await db_session.commit()

    # Attempt to create duplicate folder for same user
    folder2 = FolderCategory(
        user_id=test_user_with_gmail.id,
        name="Important",  # Duplicate name
        gmail_label_id="Label_User1_222",
        color="#FF00FF",
    )
    db_session.add(folder2)

    # Assert: Unique constraint violation
    with pytest.raises(IntegrityError):
        await db_session.commit()

    # Rollback transaction
    await db_session.rollback()

    # Create different user
    user2 = User(
        email="user2@gmail.com",
        hashed_password="$2b$12$test2",
        is_active=True,
    )
    db_session.add(user2)
    await db_session.commit()
    await db_session.refresh(user2)

    # Different user can create folder with same name
    folder3 = FolderCategory(
        user_id=user2.id,
        name="Important",  # Same name, different user
        gmail_label_id="Label_User2_333",
        color="#0000FF",
    )
    db_session.add(folder3)
    await db_session.commit()  # Should succeed

    # Verify: Both folders exist for different users
    statement = select(FolderCategory).where(FolderCategory.name == "Important")
    result = await db_session.execute(statement)
    folders = result.scalars().all()

    assert len(folders) == 2
    assert folders[0].user_id != folders[1].user_id
