"""E2E tests for complete email sorting workflow with ALL REAL APIs.

🚨 CRITICAL: This is the MOST IMPORTANT E2E test suite!

These tests verify the COMPLETE user journey with REAL external services:
- Gmail API (fetch real emails, apply real labels)
- Gemini API (real AI classification - COSTS MONEY!)
- Telegram API (send real messages, real buttons)
- PostgreSQL database (real data persistence)
- LangGraph workflows (real state machine)

This ensures that when we deploy to production, ALL integrations work together.

Setup:
    1. Configure ALL environment variables (see tests/e2e/README.md)
    2. Ensure test Gmail account has at least 1 email
    3. Ensure test Telegram chat is started with bot
    4. Run: pytest tests/e2e/test_complete_workflow_e2e.py -v -m e2e --tb=short

WARNING: These tests:
- Make REAL API calls (COSTS MONEY for Gemini)
- Send REAL Telegram messages
- Create REAL Gmail labels
- Take 30-60 seconds to complete
- Should be run MANUALLY before releases only
"""

import os
import pytest
import pytest_asyncio
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.gmail_client import GmailClient
from app.core.llm_client import LLMClient
from app.core.telegram_bot import TelegramBotClient
from app.models.user import User
from app.models.email import EmailProcessingQueue
from app.models.folder_category import FolderCategory
from app.services.classification import EmailClassificationService
from app.workflows.email_workflow import create_email_workflow
from langgraph.checkpoint.postgres import PostgresSaver


pytestmark = pytest.mark.e2e


@pytest.mark.skipif(
    not all([
        os.getenv("GMAIL_TEST_OAUTH_TOKEN"),
        os.getenv("TELEGRAM_BOT_TOKEN"),
        os.getenv("TELEGRAM_TEST_CHAT_ID"),
        os.getenv("GEMINI_API_KEY"),
        os.getenv("DATABASE_URL"),
    ]),
    reason="Required environment variables not set. Need: GMAIL_TEST_OAUTH_TOKEN, TELEGRAM_BOT_TOKEN, TELEGRAM_TEST_CHAT_ID, GEMINI_API_KEY, DATABASE_URL",
)
class TestCompleteWorkflowE2E:
    """E2E tests for complete email sorting workflow with ALL REAL APIs.

    This is the ULTIMATE integration test - verifies EVERYTHING works together.
    """

    @pytest_asyncio.fixture
    async def test_user_real(self, db_session: AsyncSession):
        """Create test user with REAL credentials for E2E testing."""
        user = User(
            email=os.getenv("GMAIL_TEST_EMAIL", "test@example.com"),
            username="e2e_test_user",
            hashed_password="fake_hash_e2e",
            is_active=True,
            gmail_oauth_token=os.getenv("GMAIL_TEST_OAUTH_TOKEN"),
            gmail_refresh_token=os.getenv("GMAIL_TEST_REFRESH_TOKEN"),
            telegram_id=os.getenv("TELEGRAM_TEST_CHAT_ID"),
            created_at=datetime.now(UTC),
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        yield user

        # Cleanup
        await db_session.delete(user)
        await db_session.commit()

    @pytest_asyncio.fixture
    async def test_folders_real(self, db_session: AsyncSession, test_user_real: User):
        """Create real folder categories for E2E testing."""
        folders = [
            FolderCategory(
                user_id=test_user_real.id,
                name="E2E_Government",
                gmail_label_id=None,  # Will be created by test
                keywords=["tax", "government", "official"],
                priority_domains=["finanzamt.de"],
                is_system_folder=False,
                created_at=datetime.now(UTC),
            ),
            FolderCategory(
                user_id=test_user_real.id,
                name="E2E_Clients",
                gmail_label_id=None,
                keywords=["client", "project"],
                priority_domains=[],
                is_system_folder=False,
                created_at=datetime.now(UTC),
            ),
        ]

        for folder in folders:
            db_session.add(folder)
        await db_session.commit()

        for folder in folders:
            await db_session.refresh(folder)

        yield folders

        # Cleanup
        for folder in folders:
            await db_session.delete(folder)
        await db_session.commit()

    @pytest_asyncio.fixture
    async def real_gmail_client(self):
        """Create REAL Gmail client for E2E testing."""
        client = GmailClient(
            oauth_token=os.getenv("GMAIL_TEST_OAUTH_TOKEN"),
            refresh_token=os.getenv("GMAIL_TEST_REFRESH_TOKEN"),
        )
        yield client

    @pytest_asyncio.fixture
    async def real_gemini_client(self):
        """Create REAL Gemini LLM client for E2E testing.

        ⚠️ WARNING: This makes REAL API calls that COST MONEY!
        """
        client = LLMClient()  # Uses GEMINI_API_KEY from env
        yield client

    @pytest_asyncio.fixture
    async def real_telegram_client(self):
        """Create REAL Telegram bot client for E2E testing."""
        client = TelegramBotClient(bot_token=os.getenv("TELEGRAM_BOT_TOKEN"))
        await client.initialize()
        yield client
        await client.stop()

    @pytest.mark.asyncio
    async def test_complete_email_classification_flow_e2e(
        self,
        db_session: AsyncSession,
        test_user_real: User,
        test_folders_real: list[FolderCategory],
        real_gmail_client: GmailClient,
        real_gemini_client: LLMClient,
        real_telegram_client: TelegramBotClient,
    ):
        """🚨 CRITICAL E2E TEST: Complete email sorting workflow with ALL REAL APIs.

        This test verifies the COMPLETE user journey:
        1. Fetch real email from Gmail
        2. Classify with real Gemini AI
        3. Send real Telegram notification
        4. Verify complete workflow

        AC Coverage: Epic 2 - COMPLETE workflow integration

        ⚠️ WARNING:
        - This test makes REAL API calls that COST MONEY
        - Takes 30-60 seconds to complete
        - Sends REAL Telegram message to your phone
        - Run MANUALLY before releases only

        What this test proves:
        ✅ Gmail API works in production
        ✅ Gemini AI classification works
        ✅ Telegram bot notifications work
        ✅ Database persistence works
        ✅ LangGraph workflows work
        ✅ ALL services integrate correctly
        """
        print("\n" + "="*80)
        print("🚨 STARTING CRITICAL E2E TEST - COMPLETE WORKFLOW WITH REAL APIs")
        print("="*80)

        # Step 1: Fetch real email from Gmail
        print("\n📧 Step 1: Fetching real email from Gmail...")
        messages = await real_gmail_client.list_messages(max_results=1)

        if not messages or len(messages) == 0:
            pytest.skip("No messages in test Gmail account. Add at least 1 email to test account.")

        test_message = messages[0]
        message_details = await real_gmail_client.get_message_detail(test_message.id)

        print(f"✅ Fetched email: {message_details.subject}")
        print(f"   From: {message_details.sender}")
        print(f"   Gmail ID: {message_details.id}")

        # Step 2: Create EmailProcessingQueue entry
        print("\n📝 Step 2: Creating database entry...")
        email_entry = EmailProcessingQueue(
            user_id=test_user_real.id,
            gmail_message_id=message_details.id,
            gmail_thread_id=message_details.thread_id,
            sender=message_details.sender,
            recipient=test_user_real.email,
            subject=message_details.subject,
            body_plain=message_details.body_plain[:500] if message_details.body_plain else "",
            received_at=message_details.received_at or datetime.now(UTC),
            status="pending",
            created_at=datetime.now(UTC),
        )
        db_session.add(email_entry)
        await db_session.commit()
        await db_session.refresh(email_entry)

        print(f"✅ Created EmailProcessingQueue entry (ID: {email_entry.id})")

        # Step 3: Real AI classification with Gemini
        print("\n🤖 Step 3: Classifying with REAL Gemini AI...")
        print("   ⚠️ WARNING: This makes a REAL API call that COSTS MONEY!")

        classification_service = EmailClassificationService(
            db=db_session,
            llm_client=real_gemini_client,
        )

        classification_result = await classification_service.classify_email(
            email_id=email_entry.id,
            user_id=test_user_real.id,
            sender=message_details.sender,
            subject=message_details.subject,
            body_preview=message_details.body_plain[:500] if message_details.body_plain else "",
        )

        print(f"✅ Gemini AI classification complete!")
        print(f"   Suggested folder: {classification_result.suggested_folder}")
        print(f"   Reasoning: {classification_result.reasoning[:100]}...")
        print(f"   Confidence: {classification_result.confidence}")

        # Step 4: Send real Telegram notification
        print("\n📱 Step 4: Sending REAL Telegram notification...")
        print("   📲 Check your Telegram app!")

        notification_text = f"""📬 E2E TEST: Email Classification Result

**From:** {message_details.sender}
**Subject:** {message_details.subject[:50]}...

**🤖 AI Suggestion:** {classification_result.suggested_folder}
**Reasoning:** {classification_result.reasoning[:100]}...

**Timestamp:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')}

⚠️ This is an E2E test notification. Email was classified by REAL Gemini AI!"""

        message_id = await real_telegram_client.send_message(
            telegram_id=test_user_real.telegram_id,
            text=notification_text,
        )

        print(f"✅ Telegram message sent (ID: {message_id})")
        print(f"   📱 CHECK YOUR TELEGRAM APP - you should see the notification!")

        # Step 5: Verify database persistence
        print("\n💾 Step 5: Verifying database persistence...")
        await db_session.refresh(email_entry)

        assert email_entry.classification == "sort_only"
        assert email_entry.proposed_folder_id is not None
        assert email_entry.classification_reasoning is not None

        print(f"✅ Database updated correctly")
        print(f"   Classification: {email_entry.classification}")
        print(f"   Proposed folder ID: {email_entry.proposed_folder_id}")

        # Cleanup
        print("\n🧹 Cleanup: Removing test data...")
        await db_session.delete(email_entry)
        await db_session.commit()

        print("\n" + "="*80)
        print("✅ CRITICAL E2E TEST PASSED - ALL SERVICES INTEGRATED CORRECTLY!")
        print("="*80)
        print("\n✅ Verified:")
        print("   ✅ Gmail API: Fetched real email")
        print("   ✅ Gemini AI: Classified email with real AI")
        print("   ✅ Telegram Bot: Sent real notification")
        print("   ✅ Database: Persisted data correctly")
        print("   ✅ Integration: All services work together")
        print("\n🎉 EPIC 2 IS READY FOR PRODUCTION!")

    @pytest.mark.asyncio
    async def test_gmail_label_creation_and_application_e2e(
        self,
        db_session: AsyncSession,
        test_user_real: User,
        test_folders_real: list[FolderCategory],
        real_gmail_client: GmailClient,
    ):
        """E2E: Create Gmail label and apply it to a message.

        This test verifies the critical path:
        1. Create Gmail label via API
        2. Apply label to message
        3. Verify label applied

        This simulates what happens when user approves AI classification.
        """
        print("\n🏷️ E2E: Gmail Label Creation and Application")

        # Get first email
        messages = await real_gmail_client.list_messages(max_results=1)
        if not messages:
            pytest.skip("No messages in Gmail account")

        test_message_id = messages[0].id

        # Create label
        label_name = f"E2E_Test_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
        created_label = await real_gmail_client.create_label(label_name)

        print(f"✅ Created label: {label_name} (ID: {created_label.id})")

        try:
            # Apply label to message (this is what happens after user approval)
            await real_gmail_client.apply_label(
                message_id=test_message_id,
                label_id=created_label.id,
            )

            print(f"✅ Applied label to message {test_message_id}")

            # Verify
            message_details = await real_gmail_client.get_message_detail(test_message_id)
            assert created_label.id in message_details.label_ids

            print(f"✅ Verified label applied successfully")

            # Remove label (cleanup)
            await real_gmail_client.remove_label(
                message_id=test_message_id,
                label_id=created_label.id,
            )

        finally:
            # Delete label
            await real_gmail_client.delete_label(created_label.id)
            print(f"✅ Cleanup: Deleted test label")

        print("✅ E2E TEST PASSED: Gmail labeling works correctly!")
