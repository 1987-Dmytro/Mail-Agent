"""Unit tests for Telegram account linking service."""

from datetime import datetime, timedelta, UTC

import pytest
from sqlmodel import Session, create_engine, select, SQLModel

from app.models.linking_codes import LinkingCode
from app.models.user import User
from app.services.telegram_linking import generate_linking_code, link_telegram_account

# Create in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture
def sqlite_session():
    """Create a fresh SQLite database session for telegram linking tests.

    Uses in-memory SQLite database for fast, isolated tests.
    Note: Renamed from sqlite_session to avoid conflict with PostgreSQL fixture.
    """
    # Create engine
    engine = create_engine(TEST_DATABASE_URL, echo=False)

    # Create only the tables needed for telegram linking tests
    User.__table__.create(engine, checkfirst=True)
    LinkingCode.__table__.create(engine, checkfirst=True)

    # Create session
    with Session(engine) as session:
        yield session

    # Drop tables after test
    LinkingCode.__table__.drop(engine, checkfirst=True)
    User.__table__.drop(engine, checkfirst=True)


@pytest.fixture
def test_user(sqlite_session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password=User.hash_password("testpassword123"),
    )
    sqlite_session.add(user)
    sqlite_session.commit()
    sqlite_session.refresh(user)
    return user


def test_generate_linking_code(sqlite_session, test_user):
    """Test that generate_linking_code creates a valid 6-character code.

    Acceptance Criteria: AC1 - Unique linking code generation implemented
    """
    # Act
    code = generate_linking_code(test_user.id, sqlite_session)

    # Assert: Code is 6 characters alphanumeric uppercase
    assert len(code) == 6
    assert code.isalnum()
    assert code.isupper()

    # Assert: Code stored in database with correct user_id
    code_record = sqlite_session.exec(
        select(LinkingCode).where(LinkingCode.code == code)
    ).first()
    assert code_record is not None
    assert code_record.user_id == test_user.id

    # Assert: expires_at is approximately 15 minutes in future
    # Handle timezone-aware comparison (works with both SQLite naive and PostgreSQL aware datetimes)
    expires_at = code_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)  # SQLite returns naive - assume UTC

    time_diff = expires_at - datetime.now(UTC)
    assert 14 * 60 < time_diff.total_seconds() < 16 * 60  # Between 14 and 16 minutes

    # Assert: used=False
    assert code_record.used is False


def test_linking_code_uniqueness(sqlite_session, test_user):
    """Test that generating multiple codes produces unique values.

    Acceptance Criteria: AC1 - Unique linking code generation implemented
    """
    # Act: Generate 100 codes
    codes = [generate_linking_code(test_user.id, sqlite_session) for _ in range(100)]

    # Assert: All codes are unique
    assert len(codes) == len(set(codes)), "All generated codes should be unique"


def test_link_telegram_account_success(sqlite_session, test_user):
    """Test successful Telegram account linking with valid code.

    Acceptance Criteria: AC4, AC5, AC8, AC9 - Bot validates code and links account
    """
    # Arrange: Generate linking code
    code = generate_linking_code(test_user.id, sqlite_session)
    telegram_id = "123456789"
    telegram_username = "testuser"

    # Act: Link Telegram account
    result = link_telegram_account(
        telegram_id=telegram_id,
        telegram_username=telegram_username,
        code=code,
        db=sqlite_session
    )

    # Assert: Success response
    assert result["success"] is True
    assert "linked successfully" in result["message"].lower()

    # Assert: User's telegram_id updated
    sqlite_session.refresh(test_user)
    assert test_user.telegram_id == telegram_id
    assert test_user.telegram_username == telegram_username
    assert test_user.telegram_linked_at is not None

    # Assert: Code marked as used
    code_record = sqlite_session.exec(
        select(LinkingCode).where(LinkingCode.code == code)
    ).first()
    assert code_record.used is True


def test_link_telegram_account_invalid_code(sqlite_session):
    """Test linking with non-existent code returns error.

    Acceptance Criteria: AC7 - Invalid codes rejected
    """
    # Arrange
    invalid_code = "XXXXXX"
    telegram_id = "123456789"

    # Act
    result = link_telegram_account(
        telegram_id=telegram_id,
        telegram_username="testuser",
        code=invalid_code,
        db=sqlite_session
    )

    # Assert
    assert result["success"] is False
    assert "invalid linking code" in result["error"].lower()


def test_link_telegram_account_expired_code(sqlite_session, test_user):
    """Test linking with expired code returns error.

    Acceptance Criteria: AC6 - Expired codes (>15 minutes old) rejected
    """
    # Arrange: Create expired linking code (set expires_at in the past)
    code = generate_linking_code(test_user.id, sqlite_session)
    code_record = sqlite_session.exec(
        select(LinkingCode).where(LinkingCode.code == code)
    ).first()
    # Set expired time using UTC for timezone-aware comparison
    code_record.expires_at = datetime.now(UTC) - timedelta(minutes=1)  # Expired 1 minute ago
    sqlite_session.commit()

    telegram_id = "123456789"

    # Act
    result = link_telegram_account(
        telegram_id=telegram_id,
        telegram_username="testuser",
        code=code,
        db=sqlite_session
    )

    # Assert
    assert result["success"] is False
    assert "expired" in result["error"].lower()


def test_link_telegram_account_used_code(sqlite_session, test_user):
    """Test that used codes cannot be reused.

    Acceptance Criteria: AC7 - Used codes cannot be reused
    """
    # Arrange: Generate code and mark as used
    code = generate_linking_code(test_user.id, sqlite_session)
    code_record = sqlite_session.exec(
        select(LinkingCode).where(LinkingCode.code == code)
    ).first()
    code_record.used = True
    sqlite_session.commit()

    telegram_id = "123456789"

    # Act
    result = link_telegram_account(
        telegram_id=telegram_id,
        telegram_username="testuser",
        code=code,
        db=sqlite_session
    )

    # Assert
    assert result["success"] is False
    assert "already been used" in result["error"].lower()


def test_link_telegram_account_already_linked_to_another_user(sqlite_session, test_user):
    """Test that Telegram account can only link to one Mail Agent account.

    Ensures one telegram_id cannot be associated with multiple users.
    """
    # Arrange: Create second user
    user2 = User(
        email="user2@example.com",
        hashed_password=User.hash_password("password123"),
    )
    sqlite_session.add(user2)
    sqlite_session.commit()
    sqlite_session.refresh(user2)

    # Link telegram_id to first user
    code1 = generate_linking_code(test_user.id, sqlite_session)
    telegram_id = "123456789"
    result1 = link_telegram_account(
        telegram_id=telegram_id,
        telegram_username="testuser",
        code=code1,
        db=sqlite_session
    )
    assert result1["success"] is True

    # Try to link same telegram_id to second user
    code2 = generate_linking_code(test_user.id, sqlite_session)
    result2 = link_telegram_account(
        telegram_id=telegram_id,  # Same Telegram ID
        telegram_username="testuser",
        code=code2,
        db=sqlite_session
    )

    # Assert: Second linking attempt fails
    assert result2["success"] is False
    assert "already linked to another" in result2["error"].lower()


def test_link_telegram_account_case_insensitive(sqlite_session, test_user):
    """Test that linking codes are case-insensitive.

    Ensures user can enter code in lowercase and it still works.
    """
    # Arrange
    code = generate_linking_code(test_user.id, sqlite_session)
    telegram_id = "123456789"

    # Act: Use lowercase code
    result = link_telegram_account(
        telegram_id=telegram_id,
        telegram_username="testuser",
        code=code.lower(),  # Lowercase version
        db=sqlite_session
    )

    # Assert: Still successful
    assert result["success"] is True
    sqlite_session.refresh(test_user)
    assert test_user.telegram_id == telegram_id
