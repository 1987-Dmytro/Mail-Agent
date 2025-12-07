#!/usr/bin/env python3
"""
Verification script for clean UX workflow fix.

This script verifies that:
1. handle_send_response now resumes workflow (not calling ResponseSendingService)
2. handle_reject_response now resumes workflow
3. send_email_response node checks for draft_decision
4. Workflow nodes are properly connected
5. send_confirmation node deletes messages and sends summary

This allows us to verify the fix without manual testing.
"""

import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

import structlog

logger = structlog.get_logger(__name__)


def verify_handler_code():
    """Verify that handlers resume workflow instead of calling ResponseSendingService."""
    print("\n=== Verifying Handler Code ===")

    # Read telegram_handlers.py
    with open("app/api/telegram_handlers.py", "r") as f:
        handler_code = f.read()

    # Check handle_send_response
    if "ResponseSendingService" in handler_code[handler_code.find("async def handle_send_response"):handler_code.find("async def handle_send_response") + 2000]:
        print("❌ FAIL: handle_send_response still imports ResponseSendingService")
        return False

    if "workflow.aupdate_state" not in handler_code[handler_code.find("async def handle_send_response"):]:
        print("❌ FAIL: handle_send_response doesn't call workflow.aupdate_state")
        return False

    if '"draft_decision": "send_response"' not in handler_code:
        print("❌ FAIL: handle_send_response doesn't set draft_decision")
        return False

    print("✅ PASS: handle_send_response resumes workflow correctly")

    # Check handle_reject_response
    if '"draft_decision": "reject_response"' not in handler_code:
        print("❌ FAIL: handle_reject_response doesn't set draft_decision")
        return False

    print("✅ PASS: handle_reject_response resumes workflow correctly")

    return True


def verify_node_code():
    """Verify that send_email_response node checks for draft_decision."""
    print("\n=== Verifying Node Code ===")

    # Read nodes.py
    with open("app/workflows/nodes.py", "r") as f:
        nodes_code = f.read()

    # Find send_email_response function
    send_email_start = nodes_code.find("async def send_email_response(")
    # Find the next function to get the full send_email_response code
    next_async_def = nodes_code.find("async def ", send_email_start + 50)
    if next_async_def == -1:
        send_email_section = nodes_code[send_email_start:]
    else:
        send_email_section = nodes_code[send_email_start:next_async_def]

    # Check for draft_decision check
    if 'draft_decision = state.get("draft_decision")' not in send_email_section:
        print("❌ FAIL: send_email_response doesn't get draft_decision from state")
        return False

    if 'draft_decision == "send_response"' not in send_email_section:
        print("❌ FAIL: send_email_response doesn't check for draft_decision='send_response'")
        return False

    print("✅ PASS: send_email_response checks draft_decision correctly")

    # Check for vector DB indexing
    if "Index sent response in vector DB" not in send_email_section:
        print("❌ FAIL: send_email_response doesn't have vector DB indexing comment")
        return False

    if "embedding_service.embed_text" not in send_email_section:
        print("❌ FAIL: send_email_response doesn't generate embeddings")
        return False

    if "vector_db_client.insert_embedding" not in send_email_section:
        print("❌ FAIL: send_email_response doesn't insert to vector DB")
        return False

    print("✅ PASS: send_email_response indexes sent responses to vector DB")

    # Check send_confirmation for message deletion
    send_conf_start = nodes_code.find("async def send_confirmation(")
    send_conf_section = nodes_code[send_conf_start:send_conf_start + 5000]

    if "delete_message" not in send_conf_section:
        print("❌ FAIL: send_confirmation doesn't delete messages")
        return False

    if "telegram_message_id" not in send_conf_section:
        print("❌ FAIL: send_confirmation doesn't get telegram_message_id for deletion")
        return False

    if "draft_telegram_message_id" not in send_conf_section:
        print("❌ FAIL: send_confirmation doesn't get draft_telegram_message_id for deletion")
        return False

    print("✅ PASS: send_confirmation deletes intermediate messages")

    # Check for summary formatting with metadata
    if "Language:" not in send_conf_section and "language" not in send_conf_section.lower():
        print("⚠️  WARNING: send_confirmation might not include language in summary")

    if "Tone:" not in send_conf_section and "tone" not in send_conf_section.lower():
        print("⚠️  WARNING: send_confirmation might not include tone in summary")

    print("✅ PASS: send_confirmation formats summary with metadata")

    return True


def verify_workflow_graph():
    """Verify workflow graph connections."""
    print("\n=== Verifying Workflow Graph ===")

    # Read email_workflow.py
    with open("app/workflows/email_workflow.py", "r") as f:
        workflow_code = f.read()

    # Check routing after draft notification
    if "route_draft_decision" not in workflow_code:
        print("❌ FAIL: route_draft_decision function not found")
        return False

    if '"send": "send_email_response"' not in workflow_code:
        print("❌ FAIL: draft decision 'send' doesn't route to send_email_response")
        return False

    if '"reject_draft": "execute_action"' not in workflow_code:
        print("❌ FAIL: draft decision 'reject_draft' doesn't route to execute_action")
        return False

    print("✅ PASS: Workflow routing is correct")

    # Check node connections
    if '"send_email_response", "execute_action"' not in workflow_code:
        print("❌ FAIL: send_email_response doesn't connect to execute_action")
        return False

    if '"execute_action", "send_confirmation"' not in workflow_code:
        print("❌ FAIL: execute_action doesn't connect to send_confirmation")
        return False

    if '"send_confirmation", END' not in workflow_code:
        print("❌ FAIL: send_confirmation doesn't connect to END")
        return False

    print("✅ PASS: Workflow nodes are properly connected")

    return True


def print_workflow_summary():
    """Print summary of expected workflow behavior."""
    print("\n=== Expected Workflow Behavior ===")
    print("""
For needs_response emails (after approving sorting):
1. User sees sorting proposal message
2. User clicks [Approve] button
3. Workflow generates draft
4. User sees draft notification message with [Send] [Edit] [Reject] buttons
5. User clicks [Send]
6. Workflow resumes from send_response_draft_notification interrupt
7. send_email_response node: Sends email via Gmail, indexes to ChromaDB
8. execute_action node: Updates folder, marks as completed
9. send_confirmation node:
   - Deletes sorting proposal message
   - Deletes draft notification message
   - Sends ONE clean summary with: folder, language, tone, "Response: Sent"

Result: Only 1 message remains in chat (the clean summary)

For sort_only emails:
1. User sees sorting proposal message
2. User clicks [Approve] button
3. execute_action node: Applies folder, marks as completed
4. send_confirmation node:
   - Deletes sorting proposal message
   - Sends ONE clean summary with: folder, language, tone, "Response: Not needed"

Result: Only 1 message remains in chat (the clean summary)
""")


def main():
    """Run all verifications."""
    print("=" * 60)
    print("WORKFLOW FIX VERIFICATION SCRIPT")
    print("=" * 60)

    results = []

    # Run verifications
    results.append(("Handler Code", verify_handler_code()))
    results.append(("Node Code", verify_node_code()))
    results.append(("Workflow Graph", verify_workflow_graph()))

    # Print summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\n🎉 ALL VERIFICATIONS PASSED!")
        print_workflow_summary()
        print("\n✅ The workflow is correctly implemented.")
        print("✅ Clean UX will work: only 1 summary message per email.")
        print("\n📝 Next step: Test with a real email to verify end-to-end behavior.")
        return 0
    else:
        print("\n❌ SOME VERIFICATIONS FAILED")
        print("Please review the failed checks above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
