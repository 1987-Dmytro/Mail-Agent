"""Unit tests for FolderCategory model.

Tests cover:
- Folder category creation with all fields
- User-folder relationship traversal
- Unique constraint on (user_id, name)
- Cascade delete when user is deleted
- Keywords array storage
"""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.models.folder_category import FolderCategory
from app.models.user import User


@pytest.mark.asyncio
async def test_folder_category_creation(db_session):
    """Test FolderCategory record creation with all fields."""
    # Create user
    user = User(
        email="test@example.com",
        hashed_password=User.hash_password("password123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create folder
    folder = FolderCategory(
        user_id=user.id,
        name="Government",
        gmail_label_id="Label_123",
        keywords=["finanzamt", "tax", "ausländerbehörde"],
        color="#FF5733",
        is_default=False,
    )
    db_session.add(folder)
    await db_session.commit()
    await db_session.refresh(folder)

    # Verify all fields
    assert folder.id is not None
    assert folder.user_id == user.id
    assert folder.name == "Government"
    assert folder.gmail_label_id == "Label_123"
    assert folder.keywords == ["finanzamt", "tax", "ausländerbehörde"]
    assert folder.color == "#FF5733"
    assert folder.is_default is False
    assert folder.created_at is not None
    assert folder.updated_at is not None


@pytest.mark.asyncio
async def test_user_folder_relationship(db_session):
    """Test bidirectional user-folder relationship traversal."""
    # Create user
    user = User(
        email="test@example.com",
        hashed_password=User.hash_password("password123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create folders
    folder1 = FolderCategory(
        user_id=user.id,
        name="Work",
        gmail_label_id="Label_123",
    )
    folder2 = FolderCategory(
        user_id=user.id,
        name="Personal",
        gmail_label_id="Label_456",
    )
    db_session.add_all([folder1, folder2])
    await db_session.commit()

    # Refresh user to load folders relationship
    await db_session.refresh(user, attribute_names=["folders"])

    # Verify relationship
    assert len(user.folders) == 2
    folder_names = {f.name for f in user.folders}
    assert folder_names == {"Work", "Personal"}

    # Verify reverse relationship
    await db_session.refresh(folder1, attribute_names=["user"])
    assert folder1.user.email == "test@example.com"


@pytest.mark.asyncio
async def test_unique_constraint_user_folder_name(db_session):
    """Test unique constraint on (user_id, name) prevents duplicates."""
    # Create user
    user = User(
        email="test@example.com",
        hashed_password=User.hash_password("password123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create first folder
    folder1 = FolderCategory(
        user_id=user.id,
        name="Government",
        gmail_label_id="Label_123",
    )
    db_session.add(folder1)
    await db_session.commit()

    # Attempt duplicate folder name for same user
    folder2 = FolderCategory(
        user_id=user.id,
        name="Government",  # Duplicate name
        gmail_label_id="Label_456",
    )
    db_session.add(folder2)

    # Verify IntegrityError raised
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_cascade_delete_folders(db_session):
    """Test cascade delete: when user deleted, all folders deleted."""
    # Create user
    user = User(
        email="test@example.com",
        hashed_password=User.hash_password("password123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create folders
    folder1 = FolderCategory(user_id=user.id, name="Work", gmail_label_id="Label_123")
    folder2 = FolderCategory(user_id=user.id, name="Personal", gmail_label_id="Label_456")
    db_session.add_all([folder1, folder2])
    await db_session.commit()

    # Verify folders exist
    result = await db_session.execute(select(FolderCategory))
    folders = result.scalars().all()
    assert len(folders) == 2

    # Delete user
    await db_session.delete(user)
    await db_session.commit()

    # Verify folders cascade deleted
    result = await db_session.execute(select(FolderCategory))
    folders = result.scalars().all()
    assert len(folders) == 0


@pytest.mark.asyncio
async def test_folder_keywords_array(db_session):
    """Test keywords field stores list correctly."""
    # Create user
    user = User(
        email="test@example.com",
        hashed_password=User.hash_password("password123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create folder with keywords
    folder = FolderCategory(
        user_id=user.id,
        name="Government",
        gmail_label_id="Label_123",
        keywords=["finanzamt", "tax", "ausländerbehörde", "government"],
    )
    db_session.add(folder)
    await db_session.commit()
    await db_session.refresh(folder)

    # Verify keywords stored correctly
    assert folder.keywords == ["finanzamt", "tax", "ausländerbehörde", "government"]
    assert isinstance(folder.keywords, list)
    assert len(folder.keywords) == 4

    # Create folder with empty keywords
    folder2 = FolderCategory(
        user_id=user.id,
        name="Work",
        gmail_label_id="Label_456",
        keywords=[],
    )
    db_session.add(folder2)
    await db_session.commit()
    await db_session.refresh(folder2)

    # Verify empty list stored correctly
    assert folder2.keywords == []
