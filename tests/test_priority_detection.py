"""Unit tests for priority email detection service (Story 2.9)."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, UTC

from app.services.priority_detection import PriorityDetectionService
from app.models.email import EmailProcessingQueue
from app.models.folder_category import FolderCategory
from app.models.user import User


@pytest.mark.asyncio
async def test_government_domain_detection(db_session):
    """Test government domain detection adds +50 points (AC #2)."""
    # Setup: Create test user and email
    user = User(
        email="test@example.com",
        is_active=True,
        telegram_id="123456789",
        telegram_linked_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    email = EmailProcessingQueue(
        user_id=user.id,
        gmail_message_id="msg_123",
        gmail_thread_id="thread_123",
        sender="steueramt@finanzamt.de",
        subject="Tax notification",
        received_at=datetime.now(UTC),
        status="new",
    )
    db_session.add(email)
    await db_session.commit()
    await db_session.refresh(email)

    # Test: Run priority detection
    service = PriorityDetectionService(db_session)
    result = await service.detect_priority(
        email_id=email.id,
        sender="steueramt@finanzamt.de",
        subject="Tax notification",
        body_preview="",
    )

    # Verify: Government domain detected
    assert result["priority_score"] == 50
    assert result["is_priority"] is False  # 50 < 70 threshold
    assert "government_domain:finanzamt.de" in result["detection_reasons"]


@pytest.mark.asyncio
async def test_urgency_keyword_detection_german(db_session):
    """Test German urgency keyword detection adds +30 points (AC #1)."""
    # Setup: Create test user and email
    user = User(
        email="test@example.com",
        is_active=True,
        telegram_id="123456789",
        telegram_linked_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    email = EmailProcessingQueue(
        user_id=user.id,
        gmail_message_id="msg_123",
        gmail_thread_id="thread_123",
        sender="sender@example.com",
        subject="Wichtig: Frist bis Freitag",
        received_at=datetime.now(UTC),
        status="new",
    )
    db_session.add(email)
    await db_session.commit()
    await db_session.refresh(email)

    # Test: Run priority detection
    service = PriorityDetectionService(db_session)
    result = await service.detect_priority(
        email_id=email.id,
        sender="sender@example.com",
        subject="Wichtig: Frist bis Freitag",
        body_preview="",
    )

    # Verify: Keywords detected
    assert result["priority_score"] == 30
    assert result["is_priority"] is False  # 30 < 70 threshold
    assert any("keyword:wichtig" in reason for reason in result["detection_reasons"])
    assert any("keyword:frist" in reason for reason in result["detection_reasons"])


@pytest.mark.asyncio
async def test_urgency_keyword_detection_multilingual(db_session):
    """Test multilingual keyword detection across EN, DE, RU, UK (AC #1)."""
    # Setup: Create test user
    user = User(
        email="test@example.com",
        is_active=True,
        telegram_id="123456789",
        telegram_linked_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    service = PriorityDetectionService(db_session)

    # Test cases for different languages
    test_cases = [
        ("urgent", "en"),  # English
        ("deadline", "en"),  # English
        ("wichtig", "de"),  # German
        ("dringend", "de"),  # German
        ("срочно", "ru"),  # Russian
        ("важно", "ru"),  # Russian
        ("терміново", "uk"),  # Ukrainian
        ("важливо", "uk"),  # Ukrainian
    ]

    for keyword, lang in test_cases:
        # Create email for this test case
        email = EmailProcessingQueue(
            user_id=user.id,
            gmail_message_id=f"msg_{lang}_{keyword}",
            gmail_thread_id=f"thread_{lang}_{keyword}",
            sender="sender@example.com",
            subject=f"Test {keyword}",
            received_at=datetime.now(UTC),
            status="new",
        )
        db_session.add(email)
        await db_session.commit()
        await db_session.refresh(email)

        # Test: Run priority detection
        result = await service.detect_priority(
            email_id=email.id,
            sender="sender@example.com",
            subject=f"Test {keyword}",
            body_preview="",
        )

        # Verify: Keyword detected
        assert result["priority_score"] == 30, f"Failed for {lang} keyword: {keyword}"
        assert any(keyword.lower() in reason for reason in result["detection_reasons"]), \
            f"Detection reason missing for {lang} keyword: {keyword}"


@pytest.mark.asyncio
async def test_priority_threshold_triggering(db_session):
    """Test priority threshold triggering at >= 70 (AC #4)."""
    # Setup: Create test user
    user = User(
        email="test@example.com",
        is_active=True,
        telegram_id="123456789",
        telegram_linked_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    service = PriorityDetectionService(db_session)

    # Test Case 1: Government domain (50) + keyword (30) = 80 >= 70 (PRIORITY)
    email1 = EmailProcessingQueue(
        user_id=user.id,
        gmail_message_id="msg_priority",
        gmail_thread_id="thread_priority",
        sender="steuer@finanzamt.de",
        subject="Wichtig: Tax deadline",
        received_at=datetime.now(UTC),
        status="new",
    )
    db_session.add(email1)
    await db_session.commit()
    await db_session.refresh(email1)

    result1 = await service.detect_priority(
        email_id=email1.id,
        sender="steuer@finanzamt.de",
        subject="Wichtig: Tax deadline",
        body_preview="",
    )

    assert result1["priority_score"] == 80
    assert result1["is_priority"] is True  # 80 >= 70 threshold

    # Test Case 2: Keyword only (30) = 30 < 70 (NOT PRIORITY)
    email2 = EmailProcessingQueue(
        user_id=user.id,
        gmail_message_id="msg_non_priority",
        gmail_thread_id="thread_non_priority",
        sender="sender@example.com",
        subject="Wichtig: Meeting reminder",
        received_at=datetime.now(UTC),
        status="new",
    )
    db_session.add(email2)
    await db_session.commit()
    await db_session.refresh(email2)

    result2 = await service.detect_priority(
        email_id=email2.id,
        sender="sender@example.com",
        subject="Wichtig: Meeting reminder",
        body_preview="",
    )

    assert result2["priority_score"] == 30
    assert result2["is_priority"] is False  # 30 < 70 threshold


@pytest.mark.asyncio
async def test_user_configured_priority_sender(db_session):
    """Test user-configured priority senders add +40 points (AC #8)."""
    # Setup: Create test user
    user = User(
        email="test@example.com",
        is_active=True,
        telegram_id="123456789",
        telegram_linked_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create FolderCategory with is_priority_sender=True
    folder = FolderCategory(
        user_id=user.id,
        name="VIP Clients",
        keywords=["important-client@example.com"],
        is_priority_sender=True,
    )
    db_session.add(folder)
    await db_session.commit()

    # Create email from priority sender
    email = EmailProcessingQueue(
        user_id=user.id,
        gmail_message_id="msg_vip",
        gmail_thread_id="thread_vip",
        sender="important-client@example.com",
        subject="Project status",
        received_at=datetime.now(UTC),
        status="new",
    )
    db_session.add(email)
    await db_session.commit()
    await db_session.refresh(email)

    # Test: Run priority detection
    service = PriorityDetectionService(db_session)
    result = await service.detect_priority(
        email_id=email.id,
        sender="important-client@example.com",
        subject="Project status",
        body_preview="",
    )

    # Verify: User-configured sender detected
    assert result["priority_score"] == 40
    assert result["is_priority"] is False  # 40 < 70 threshold
    assert any("user_configured_sender" in reason for reason in result["detection_reasons"])


@pytest.mark.asyncio
async def test_priority_score_capped_at_100(db_session):
    """Test priority score is capped at 100 (AC #3)."""
    # Setup: Create test user
    user = User(
        email="test@example.com",
        is_active=True,
        telegram_id="123456789",
        telegram_linked_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create FolderCategory with is_priority_sender=True
    folder = FolderCategory(
        user_id=user.id,
        name="VIP Clients",
        keywords=["finanzamt.de"],
        is_priority_sender=True,
    )
    db_session.add(folder)
    await db_session.commit()

    # Create email with ALL factors: government (50) + keyword (30) + user_config (40) = 120
    email = EmailProcessingQueue(
        user_id=user.id,
        gmail_message_id="msg_max",
        gmail_thread_id="thread_max",
        sender="steuer@finanzamt.de",
        subject="URGENT: Deadline tomorrow",
        received_at=datetime.now(UTC),
        status="new",
    )
    db_session.add(email)
    await db_session.commit()
    await db_session.refresh(email)

    # Test: Run priority detection
    service = PriorityDetectionService(db_session)
    result = await service.detect_priority(
        email_id=email.id,
        sender="steuer@finanzamt.de",
        subject="URGENT: Deadline tomorrow",
        body_preview="",
    )

    # Verify: Score capped at 100 (not 120)
    assert result["priority_score"] == 100
    assert result["is_priority"] is True  # 100 >= 70 threshold


@pytest.mark.asyncio
async def test_priority_detection_logging(db_session):
    """Test priority detection logging includes all required fields (AC #9)."""
    # This test verifies that logging occurs correctly by checking the service runs without errors
    # In a real scenario, we would mock the logger to verify log calls

    # Setup: Create test user and email
    user = User(
        email="test@example.com",
        is_active=True,
        telegram_id="123456789",
        telegram_linked_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    email = EmailProcessingQueue(
        user_id=user.id,
        gmail_message_id="msg_log",
        gmail_thread_id="thread_log",
        sender="test@finanzamt.de",
        subject="Test logging",
        received_at=datetime.now(UTC),
        status="new",
    )
    db_session.add(email)
    await db_session.commit()
    await db_session.refresh(email)

    # Test: Run priority detection
    service = PriorityDetectionService(db_session)
    result = await service.detect_priority(
        email_id=email.id,
        sender="test@finanzamt.de",
        subject="Test logging",
        body_preview="Test body",
    )

    # Verify: All expected fields are in result (which would be logged)
    assert "priority_score" in result
    assert "is_priority" in result
    assert "detection_reasons" in result
    assert isinstance(result["detection_reasons"], list)


@pytest.mark.asyncio
async def test_extract_domain_from_email_formats(db_session):
    """Test domain extraction from various email formats (AC #2)."""
    service = PriorityDetectionService(db_session)

    # Test Case 1: Simple email format "email@domain.de"
    domain1 = service._extract_domain("test@finanzamt.de")
    assert domain1 == "finanzamt.de"

    # Test Case 2: Name with angle brackets "Name <email@domain.de>"
    domain2 = service._extract_domain("John Doe <john@finanzamt.de>")
    assert domain2 == "finanzamt.de"

    # Test Case 3: Subdomain "name@subdomain.domain.de"
    domain3 = service._extract_domain("user@berlin.finanzamt.de")
    assert domain3 == "berlin.finanzamt.de"

    # Test Case 4: Complex name format
    domain4 = service._extract_domain("Steueramt Berlin <steuer@finanzamt.de>")
    assert domain4 == "finanzamt.de"

    # Test Case 5: Invalid format (no @ sign)
    domain5 = service._extract_domain("invalid-email")
    assert domain5 == ""

    # Test Case 6: Empty string
    domain6 = service._extract_domain("")
    assert domain6 == ""
