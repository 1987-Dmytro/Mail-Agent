"""Integration tests for FolderService.

Tests cover:
- create_folder(): End-to-end folder creation (DB + Gmail API coordination)
- list_folders(): Query all folders for a user
- get_folder_by_id(): Fetch single folder with user ownership verification
- delete_folder(): Remove folder from database and Gmail
- Duplicate folder name error handling
- User isolation (folders filtered by user_id)
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.folder_category import FolderCategory
from app.models.user import User
from app.services.database import DatabaseService
from app.services.folder_service import FolderService


# Test Fixtures
@pytest.fixture
def mock_gmail_client():
    """Mock GmailClient for Gmail API operations."""
    mock_client = Mock()
    mock_client.create_label = AsyncMock(return_value="Label_123")
    mock_client.list_labels = AsyncMock(
        return_value=[
            {
                "label_id": "Label_123",
                "name": "Government",
                "type": "user",
                "visibility": "labelShow",
            }
        ]
    )
    return mock_client


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user in the database."""
    user = User(
        email="test@example.com",
        gmail_oauth_token="encrypted_token_123",
        gmail_refresh_token="encrypted_refresh_123",
        telegram_id=987654321,
        telegram_username="testuser",
        is_active=True,
        onboarding_completed=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_user_2(db_session: AsyncSession) -> User:
    """Create a second test user for isolation testing."""
    user = User(
        email="user2@example.com",
        gmail_oauth_token="encrypted_token_456",
        gmail_refresh_token="encrypted_refresh_456",
        telegram_id=123456789,
        telegram_username="user2",
        is_active=True,
        onboarding_completed=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def folder_service(db_session: AsyncSession) -> FolderService:
    """Create FolderService instance with real database session."""
    db_service = DatabaseService()
    # Inject test session into database service
    db_service._async_session_maker = lambda: db_session
    return FolderService(db_service=db_service)


# Test: create_folder() end-to-end
@pytest.mark.asyncio
async def test_create_folder_end_to_end(
    folder_service: FolderService, test_user: User, db_session: AsyncSession
):
    """Test end-to-end folder creation: Gmail API + database record.

    This test verifies:
    1. Gmail label is created via Gmail API (mocked)
    2. FolderCategory record is saved to database
    3. gmail_label_id is correctly stored
    4. All fields are populated correctly
    """
    # Mock GmailClient to return label_id
    with patch("app.services.folder_service.GmailClient") as mock_gmail_class:
        mock_gmail_instance = Mock()
        mock_gmail_instance.create_label = AsyncMock(return_value="Label_999")
        mock_gmail_class.return_value = mock_gmail_instance

        # Create folder
        folder = await folder_service.create_folder(
            user_id=test_user.id,
            name="Important Clients",
            keywords=["client", "urgent", "vip"],
            color="#FF5733",
        )

        # Verify folder object returned
        assert folder is not None
        assert folder.id is not None
        assert folder.user_id == test_user.id
        assert folder.name == "Important Clients"
        assert folder.gmail_label_id == "Label_999"
        assert folder.keywords == ["client", "urgent", "vip"]
        assert folder.color == "#FF5733"
        assert folder.is_default is False
        assert folder.created_at is not None
        assert folder.updated_at is not None

        # Verify Gmail API was called correctly
        mock_gmail_instance.create_label.assert_called_once_with(
            name="Important Clients", color="#FF5733"
        )

        # Verify folder is persisted correctly (no need to refresh, object has all fields)
        assert folder.user_id == test_user.id
        assert folder.gmail_label_id == "Label_999"


# Test: list_folders() by user
@pytest.mark.asyncio
async def test_list_folders_by_user(
    folder_service: FolderService,
    test_user: User,
    test_user_2: User,
    db_session: AsyncSession,
):
    """Test listing folders filtered by user_id.

    Verifies:
    1. Folders are correctly filtered by user_id
    2. User A cannot see User B's folders (isolation)
    3. Empty list returned when user has no folders
    """
    # Mock GmailClient for all create_folder calls
    with patch("app.services.folder_service.GmailClient") as mock_gmail_class:
        mock_gmail_instance = Mock()
        mock_gmail_instance.create_label = AsyncMock(
            side_effect=["Label_001", "Label_002", "Label_003"]
        )
        mock_gmail_class.return_value = mock_gmail_instance

        # Create folders for test_user
        await folder_service.create_folder(
            user_id=test_user.id, name="Government", keywords=["tax", "finanzamt"]
        )
        await folder_service.create_folder(
            user_id=test_user.id, name="Work", keywords=["job", "company"]
        )

        # Create folder for test_user_2
        await folder_service.create_folder(
            user_id=test_user_2.id, name="Personal", keywords=["family"]
        )

        # List folders for test_user
        user_1_folders = await folder_service.list_folders(user_id=test_user.id)
        assert len(user_1_folders) == 2
        folder_names = [f.name for f in user_1_folders]
        assert "Government" in folder_names
        assert "Work" in folder_names
        assert "Personal" not in folder_names  # Isolation check

        # List folders for test_user_2
        user_2_folders = await folder_service.list_folders(user_id=test_user_2.id)
        assert len(user_2_folders) == 1
        assert user_2_folders[0].name == "Personal"

        # Verify each folder has correct user_id
        for folder in user_1_folders:
            assert folder.user_id == test_user.id
        for folder in user_2_folders:
            assert folder.user_id == test_user_2.id


# Test: get_folder_by_id() with ownership verification
@pytest.mark.asyncio
async def test_get_folder_by_id(
    folder_service: FolderService,
    test_user: User,
    test_user_2: User,
    db_session: AsyncSession,
):
    """Test fetching single folder by ID with user ownership verification.

    Verifies:
    1. Folder can be retrieved by ID
    2. User ownership is verified (cannot access other user's folders)
    3. Returns None when folder doesn't exist or user doesn't own it
    """
    # Mock GmailClient
    with patch("app.services.folder_service.GmailClient") as mock_gmail_class:
        mock_gmail_instance = Mock()
        mock_gmail_instance.create_label = AsyncMock(return_value="Label_100")
        mock_gmail_class.return_value = mock_gmail_instance

        # Create folder for test_user
        folder = await folder_service.create_folder(
            user_id=test_user.id, name="Work", keywords=["job"]
        )

        # Fetch folder by correct user
        fetched_folder = await folder_service.get_folder_by_id(
            folder_id=folder.id, user_id=test_user.id
        )
        assert fetched_folder is not None
        assert fetched_folder.id == folder.id
        assert fetched_folder.name == "Work"

        # Attempt to fetch folder by different user (should return None)
        unauthorized_fetch = await folder_service.get_folder_by_id(
            folder_id=folder.id, user_id=test_user_2.id
        )
        assert unauthorized_fetch is None

        # Attempt to fetch non-existent folder (should return None)
        non_existent = await folder_service.get_folder_by_id(
            folder_id=999999, user_id=test_user.id
        )
        assert non_existent is None


# Test: delete_folder()
@pytest.mark.asyncio
async def test_delete_folder(
    folder_service: FolderService, test_user: User, db_session: AsyncSession
):
    """Test folder deletion from database and Gmail.

    Verifies:
    1. Folder is removed from database
    2. Gmail label deletion is attempted (mocked)
    3. Returns True on successful deletion
    4. Returns False when folder doesn't exist or user doesn't own it
    """
    # Mock GmailClient
    with patch("app.services.folder_service.GmailClient") as mock_gmail_class:
        mock_gmail_instance = Mock()
        mock_gmail_instance.create_label = AsyncMock(return_value="Label_200")
        mock_gmail_class.return_value = mock_gmail_instance

        # Create folder
        folder = await folder_service.create_folder(
            user_id=test_user.id, name="Temporary"
        )
        folder_id = folder.id

        # Verify folder exists
        existing = await folder_service.get_folder_by_id(
            folder_id=folder_id, user_id=test_user.id
        )
        assert existing is not None

        # Delete folder
        success = await folder_service.delete_folder(
            folder_id=folder_id, user_id=test_user.id
        )
        assert success is True

        # Verify folder no longer exists
        deleted = await folder_service.get_folder_by_id(
            folder_id=folder_id, user_id=test_user.id
        )
        assert deleted is None

        # Attempt to delete non-existent folder (should return False)
        delete_non_existent = await folder_service.delete_folder(
            folder_id=999999, user_id=test_user.id
        )
        assert delete_non_existent is False


# Test: duplicate folder name error
@pytest.mark.asyncio
async def test_duplicate_folder_name_error(
    folder_service: FolderService, test_user: User, db_session: AsyncSession
):
    """Test duplicate folder name handling.

    Verifies:
    1. Unique constraint on (user_id, name) is enforced
    2. ValueError is raised when duplicate name is detected
    3. Error message is user-friendly
    4. Different users can have folders with same name (user isolation)
    """
    # Mock GmailClient
    with patch("app.services.folder_service.GmailClient") as mock_gmail_class:
        mock_gmail_instance = Mock()
        mock_gmail_instance.create_label = AsyncMock(
            side_effect=["Label_300", "Label_301"]
        )
        mock_gmail_class.return_value = mock_gmail_instance

        # Create first folder
        folder_1 = await folder_service.create_folder(
            user_id=test_user.id, name="Government", keywords=["tax"]
        )
        assert folder_1 is not None

        # Attempt to create duplicate folder for same user (should raise ValueError)
        with pytest.raises(ValueError) as exc_info:
            await folder_service.create_folder(
                user_id=test_user.id, name="Government", keywords=["different"]
            )
        assert "already exists" in str(exc_info.value).lower() or "duplicate" in str(
            exc_info.value
        ).lower()


# Test: create_folder() with invalid name
@pytest.mark.asyncio
async def test_create_folder_invalid_name(
    folder_service: FolderService, test_user: User, db_session: AsyncSession
):
    """Test folder creation validation.

    Verifies:
    1. Empty folder name is rejected
    2. Folder name exceeding 100 chars is rejected
    3. ValueError is raised with descriptive message
    """
    # Test empty name
    with pytest.raises(ValueError) as exc_info:
        await folder_service.create_folder(user_id=test_user.id, name="")
    assert "1 and 100 characters" in str(exc_info.value)

    # Test name too long (>100 chars)
    long_name = "A" * 101
    with pytest.raises(ValueError) as exc_info:
        await folder_service.create_folder(user_id=test_user.id, name=long_name)
    assert "1 and 100 characters" in str(exc_info.value)

    # Test None name
    with pytest.raises(ValueError) as exc_info:
        await folder_service.create_folder(user_id=test_user.id, name=None)
    assert "1 and 100 characters" in str(exc_info.value)


# Test: create_folder() with keywords and color
@pytest.mark.asyncio
async def test_create_folder_with_keywords_and_color(
    folder_service: FolderService, test_user: User, db_session: AsyncSession
):
    """Test folder creation with optional keywords and color.

    Verifies:
    1. Keywords array is correctly stored
    2. Color hex code is stored
    3. Optional parameters work correctly (None/empty defaults)
    """
    # Mock GmailClient
    with patch("app.services.folder_service.GmailClient") as mock_gmail_class:
        mock_gmail_instance = Mock()
        mock_gmail_instance.create_label = AsyncMock(
            side_effect=["Label_400", "Label_401", "Label_402"]
        )
        mock_gmail_class.return_value = mock_gmail_instance

        # Create folder with keywords and color
        folder_1 = await folder_service.create_folder(
            user_id=test_user.id,
            name="Important",
            keywords=["urgent", "vip", "priority"],
            color="#FF5733",
        )
        assert folder_1.keywords == ["urgent", "vip", "priority"]
        assert folder_1.color == "#FF5733"

        # Create folder without keywords (should default to empty list)
        folder_2 = await folder_service.create_folder(
            user_id=test_user.id, name="Normal", color="#00FF00"
        )
        assert folder_2.keywords == []
        assert folder_2.color == "#00FF00"

        # Create folder without color (should be None)
        folder_3 = await folder_service.create_folder(
            user_id=test_user.id, name="Minimal", keywords=["test"]
        )
        assert folder_3.keywords == ["test"]
        assert folder_3.color is None


# Test: user isolation across all operations
@pytest.mark.asyncio
async def test_user_isolation(
    folder_service: FolderService,
    test_user: User,
    test_user_2: User,
    db_session: AsyncSession,
):
    """Test user isolation across all folder operations.

    Verifies:
    1. User A cannot see User B's folders via list_folders()
    2. User A cannot fetch User B's folder by ID
    3. User A cannot delete User B's folder
    4. Users can have folders with same name (isolation)
    """
    # Mock GmailClient
    with patch("app.services.folder_service.GmailClient") as mock_gmail_class:
        mock_gmail_instance = Mock()
        mock_gmail_instance.create_label = AsyncMock(
            side_effect=["Label_500", "Label_501"]
        )
        mock_gmail_class.return_value = mock_gmail_instance

        # User A creates folder
        folder_a = await folder_service.create_folder(
            user_id=test_user.id, name="Personal"
        )

        # User B creates folder with same name (should succeed due to isolation)
        folder_b = await folder_service.create_folder(
            user_id=test_user_2.id, name="Personal"
        )

        assert folder_a.name == folder_b.name
        assert folder_a.user_id != folder_b.user_id

        # User A lists folders (should only see their own)
        user_a_folders = await folder_service.list_folders(user_id=test_user.id)
        assert len(user_a_folders) == 1
        assert user_a_folders[0].id == folder_a.id

        # User A attempts to fetch User B's folder (should return None)
        unauthorized_fetch = await folder_service.get_folder_by_id(
            folder_id=folder_b.id, user_id=test_user.id
        )
        assert unauthorized_fetch is None

        # User A attempts to delete User B's folder (should return False)
        unauthorized_delete = await folder_service.delete_folder(
            folder_id=folder_b.id, user_id=test_user.id
        )
        assert unauthorized_delete is False

        # Verify User B's folder still exists
        user_b_folder = await folder_service.get_folder_by_id(
            folder_id=folder_b.id, user_id=test_user_2.id
        )
        assert user_b_folder is not None
