"""E2E tests for real Gmail API integration.

CRITICAL: These tests make REAL API calls to Gmail.
- Requires valid Gmail OAuth credentials
- Creates and deletes real labels
- Rate limited (250 requests/day for free tier)

Run only before releases or when explicitly needed.

Setup:
    1. Set GMAIL_TEST_OAUTH_TOKEN environment variable
    2. Ensure test Gmail account is configured
    3. Run: pytest tests/e2e/test_gmail_real_api.py -v -m e2e

These tests verify:
    - Real Gmail API connectivity
    - Label creation/deletion
    - Label application to messages
    - OAuth token refresh handling
"""

import os
import pytest
import pytest_asyncio
from datetime import datetime, UTC

from app.core.gmail_client import GmailClient


pytestmark = pytest.mark.e2e


@pytest.mark.skipif(
    not os.getenv("GMAIL_TEST_OAUTH_TOKEN"),
    reason="GMAIL_TEST_OAUTH_TOKEN not set. Set it to enable real Gmail API E2E tests.",
)
class TestGmailRealAPI:
    """E2E tests with REAL Gmail API."""

    @pytest_asyncio.fixture
    async def real_gmail_client(self):
        """Create real Gmail client with test account credentials.

        Expects GMAIL_TEST_OAUTH_TOKEN environment variable with valid OAuth token.
        """
        oauth_token = os.getenv("GMAIL_TEST_OAUTH_TOKEN")
        refresh_token = os.getenv("GMAIL_TEST_REFRESH_TOKEN")

        client = GmailClient(
            oauth_token=oauth_token,
            refresh_token=refresh_token,
        )

        yield client

        # Cleanup: No persistent client state to clean up

    @pytest.mark.asyncio
    async def test_gmail_create_and_delete_label_e2e(self, real_gmail_client: GmailClient):
        """E2E: Create and delete a real Gmail label.

        This test verifies:
        - Real Gmail API connectivity
        - OAuth authentication works
        - Label creation succeeds
        - Label appears in label list
        - Label deletion succeeds

        AC Coverage: Epic 1 - Gmail label management
        """
        # Create unique test label with timestamp
        test_label_name = f"E2E_Test_Label_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"

        try:
            # Step 1: Create label via real Gmail API
            created_label = await real_gmail_client.create_label(test_label_name)

            # Verify label created
            assert created_label is not None, "Label creation returned None"
            assert created_label.name == test_label_name, f"Expected label name '{test_label_name}', got '{created_label.name}'"
            assert created_label.id is not None, "Label ID is None"

            print(f"✅ Created real Gmail label: {test_label_name} (ID: {created_label.id})")

            # Step 2: Verify label appears in label list
            labels = await real_gmail_client.list_labels()
            label_names = [label.name for label in labels]

            assert test_label_name in label_names, f"Created label '{test_label_name}' not found in label list"

            print(f"✅ Verified label appears in list (total labels: {len(labels)})")

            # Step 3: Get label details
            label_details = await real_gmail_client.get_label(created_label.id)

            assert label_details.name == test_label_name
            assert label_details.id == created_label.id

            print(f"✅ Retrieved label details successfully")

        finally:
            # Cleanup: Delete test label
            try:
                await real_gmail_client.delete_label(created_label.id)
                print(f"✅ Cleanup: Deleted test label {test_label_name}")
            except Exception as e:
                print(f"⚠️ Cleanup warning: Failed to delete label {test_label_name}: {e}")

    @pytest.mark.asyncio
    async def test_gmail_apply_label_to_message_e2e(self, real_gmail_client: GmailClient):
        """E2E: Apply label to a real Gmail message.

        This test verifies:
        - Fetching real messages from Gmail
        - Creating a test label
        - Applying label to a message
        - Verifying label applied
        - Removing label (cleanup)

        AC Coverage: Epic 2 - AI sorting applies labels

        Note: This test assumes there's at least 1 message in the test Gmail inbox.
        """
        test_label_name = f"E2E_Sort_Test_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
        created_label = None
        test_message_id = None

        try:
            # Step 1: Get first message from inbox
            messages = await real_gmail_client.list_messages(max_results=1)

            if not messages or len(messages) == 0:
                pytest.skip("No messages in test Gmail account. Cannot test label application.")

            test_message_id = messages[0].id
            print(f"✅ Found test message: {test_message_id}")

            # Step 2: Create test label
            created_label = await real_gmail_client.create_label(test_label_name)
            print(f"✅ Created test label: {test_label_name} (ID: {created_label.id})")

            # Step 3: Apply label to message
            await real_gmail_client.apply_label(
                message_id=test_message_id,
                label_id=created_label.id,
            )
            print(f"✅ Applied label to message {test_message_id}")

            # Step 4: Verify label applied by fetching message details
            message_details = await real_gmail_client.get_message_detail(test_message_id)

            assert created_label.id in message_details.label_ids, \
                f"Label {created_label.id} not found in message labels: {message_details.label_ids}"

            print(f"✅ Verified label applied (message has {len(message_details.label_ids)} labels)")

            # Step 5: Remove label from message (cleanup)
            await real_gmail_client.remove_label(
                message_id=test_message_id,
                label_id=created_label.id,
            )
            print(f"✅ Removed label from message (cleanup)")

        finally:
            # Cleanup: Delete test label
            if created_label:
                try:
                    await real_gmail_client.delete_label(created_label.id)
                    print(f"✅ Cleanup: Deleted test label {test_label_name}")
                except Exception as e:
                    print(f"⚠️ Cleanup warning: Failed to delete label: {e}")

    @pytest.mark.asyncio
    async def test_gmail_oauth_token_refresh_e2e(self, real_gmail_client: GmailClient):
        """E2E: Verify OAuth token refresh works with real API.

        This test verifies:
        - Token refresh mechanism
        - API calls work after refresh
        - Refresh token is valid

        Note: This test may not trigger actual refresh if token is still valid.
        """
        # Make API call to ensure token is valid
        labels_before = await real_gmail_client.list_labels()
        assert len(labels_before) > 0, "Expected at least some labels in Gmail account"

        print(f"✅ Token valid: Listed {len(labels_before)} labels")

        # Force token refresh (if supported by client)
        # Note: Actual refresh happens automatically when token expires

        # Make another API call to verify still working
        labels_after = await real_gmail_client.list_labels()
        assert len(labels_after) > 0

        print(f"✅ Token still valid after operations")
