#!/usr/bin/env python3
"""
Debug Script: Verify sender_history is included in response generation prompt

This script will:
1. Find "Re: Праздники" email
2. Retrieve full RAG context (including sender_history)
3. Format the actual prompt that would be sent to Gemini
4. Display sender_history content and prompt structure
5. Identify why LLM might not be using sender_history
"""

import asyncio
import os
import sys
from datetime import datetime

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from sqlalchemy import select

from app.services.database import database_service
from app.models.email import EmailProcessingQueue
from app.services.context_retrieval import ContextRetrievalService
from app.prompts.response_generation import format_response_prompt


async def debug_sender_history_in_prompt():
    """Debug sender_history integration in response generation."""

    print("=" * 80)
    print("DEBUG: Sender History in Response Generation Prompt")
    print("=" * 80)

    async with database_service.async_session() as session:
        # 1. Find "Re: Праздники" email
        print("\n📧 Step 1: Finding 'Re: Праздники' email...")

        result = await session.execute(
            select(EmailProcessingQueue)
            .where(EmailProcessingQueue.subject.like("%раздники%"))
            .where(EmailProcessingQueue.classification == "needs_response")
            .order_by(EmailProcessingQueue.received_at.desc())
            .limit(1)
        )
        email = result.scalar_one_or_none()

        if not email:
            print("❌ Email 'Re: Праздники' not found")
            print("\n🔍 Looking for ANY email that needs response...")
            result = await session.execute(
                select(EmailProcessingQueue)
                .where(EmailProcessingQueue.classification == "needs_response")
                .order_by(EmailProcessingQueue.received_at.desc())
                .limit(1)
            )
            email = result.scalar_one_or_none()

            if not email:
                print("❌ No emails needing response found")
                return False

        print(f"\n✅ Testing with email:")
        print(f"   ID: {email.id}")
        print(f"   Subject: {email.subject}")
        print(f"   From: {email.sender}")
        print(f"   Date: {email.received_at}")
        print(f"   Language: {email.detected_language}")
        print(f"   Tone: {email.tone}")

        # 2. Retrieve RAG context
        print("\n🔍 Step 2: Retrieving RAG context...")
        print("-" * 80)

        context_service = ContextRetrievalService(
            user_id=email.user_id,
            session=session
        )

        rag_context = await context_service.retrieve_context(
            email_id=email.id,
            user_id=email.user_id
        )

        # Display context breakdown
        print(f"\n📊 RAG Context Retrieved:")
        print(f"   Thread History: {len(rag_context['thread_history'])} emails")
        print(f"   Sender History: {len(rag_context['sender_history'])} emails ⭐ KEY")
        print(f"   Semantic Results: {len(rag_context['semantic_results'])} emails")
        print(f"   Total Context: {rag_context['metadata']['total_context_emails']}")

        # 3. Examine sender_history in detail
        print("\n📧 Step 3: Examining sender_history content...")
        print("-" * 80)

        if not rag_context['sender_history']:
            print("❌ PROBLEM FOUND: sender_history is EMPTY!")
            print("   This explains why LLM doesn't use it - no data was retrieved")
            return False

        print(f"\n✅ sender_history has {len(rag_context['sender_history'])} emails:")
        print("   (Showing first 5 emails)\n")

        for i, email_msg in enumerate(rag_context['sender_history'][:5], 1):
            subject = email_msg.get('subject', 'No subject')
            date = email_msg.get('date', 'Unknown date')
            body = email_msg.get('body', '')
            sender = email_msg.get('sender', 'Unknown')

            print(f"   {i}. [{date}] {subject}")
            print(f"      From: {sender}")
            print(f"      Body length: {len(body)} chars")

            if len(body) > 0:
                print(f"      Body preview: {body[:100]}...")
            else:
                print(f"      ⚠️  WARNING: Body is EMPTY!")

            print()

        if len(rag_context['sender_history']) > 5:
            print(f"   ... and {len(rag_context['sender_history']) - 5} more emails")

        # Check if bodies are empty
        empty_bodies = sum(1 for e in rag_context['sender_history'] if not e.get('body', '').strip())
        if empty_bodies > 0:
            print(f"\n⚠️  WARNING: {empty_bodies}/{len(rag_context['sender_history'])} emails have EMPTY bodies!")
            print("   This means LLM has NO context from sender history!")

        # 4. Format the actual prompt
        print("\n✨ Step 4: Formatting actual prompt for Gemini...")
        print("-" * 80)

        try:
            formatted_prompt = format_response_prompt(
                email=email,
                rag_context=rag_context,
                language=email.detected_language or 'en',
                tone=email.tone or 'professional'
            )

            prompt_length = len(formatted_prompt)
            sender_history_section = "Full Conversation History with Sender (Last 90 Days):" in formatted_prompt

            print(f"\n✅ Prompt formatted successfully:")
            print(f"   Total length: {prompt_length} characters")
            print(f"   Sender history section present: {sender_history_section}")

            # Find and display sender_history section
            if sender_history_section:
                start = formatted_prompt.find("Full Conversation History with Sender (Last 90 Days):")
                end = formatted_prompt.find("Relevant Context from Previous Emails (Semantic Search):")

                if start != -1 and end != -1:
                    sender_history_text = formatted_prompt[start:end].strip()
                    print(f"\n📄 Sender History Section ({len(sender_history_text)} chars):")
                    print("   " + "-" * 76)

                    # Show first 1000 chars of sender_history section
                    preview = sender_history_text[:1000]
                    print(f"   {preview}")

                    if len(sender_history_text) > 1000:
                        print(f"   ... [truncated, total {len(sender_history_text)} chars]")

                    print("   " + "-" * 76)

                    # Check if section is just "No sender history available"
                    if "No sender history available" in sender_history_text:
                        print("\n❌ PROBLEM FOUND: Sender history section says 'No sender history available'")
                        print("   Even though we retrieved sender_history above!")
                        return False
            else:
                print("\n❌ PROBLEM FOUND: Sender history section NOT in prompt!")
                return False

            # 5. Save full prompt to file for inspection
            debug_file = "debug_prompt_output.txt"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("FULL PROMPT SENT TO GEMINI API\n")
                f.write("=" * 80 + "\n\n")
                f.write(formatted_prompt)
                f.write("\n\n" + "=" * 80 + "\n")
                f.write("END OF PROMPT\n")
                f.write("=" * 80 + "\n")

            print(f"\n✅ Full prompt saved to: {debug_file}")
            print("   You can inspect the complete prompt manually")

        except Exception as e:
            print(f"\n❌ Failed to format prompt: {e}")
            import traceback
            traceback.print_exc()
            return False

        # 6. Final analysis
        print("\n" + "=" * 80)
        print("FINAL ANALYSIS")
        print("=" * 80)

        checks = []

        # Check 1: sender_history retrieved?
        sender_history_ok = len(rag_context['sender_history']) > 0
        checks.append(("sender_history retrieved", sender_history_ok))

        # Check 2: sender_history has content?
        bodies_ok = empty_bodies < len(rag_context['sender_history'])
        checks.append(("sender_history has body content", bodies_ok))

        # Check 3: sender_history in prompt?
        prompt_ok = sender_history_section
        checks.append(("sender_history in formatted prompt", prompt_ok))

        # Check 4: Prompt not too long?
        token_limit_ok = prompt_length < 30000  # Gemini has 32K token limit (~128K chars)
        checks.append(("prompt within token limits", token_limit_ok))

        print("\n✅ Diagnostic Checks:")
        for check_name, passed in checks:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {status}: {check_name}")

        passed_count = sum(1 for _, passed in checks if passed)
        total_checks = len(checks)

        print(f"\n📊 Overall: {passed_count}/{total_checks} checks passed")

        if passed_count == total_checks:
            print("\n" + "=" * 80)
            print("✅ SUCCESS: sender_history is correctly integrated!")
            print("=" * 80)
            print("\nConclusion:")
            print("✅ Context retrieval working")
            print("✅ Prompt formatting working")
            print("✅ sender_history included in prompt")
            print("\n⚠️  If LLM still doesn't use context, the issue is:")
            print("   1. LLM not following instructions (need stronger prompt)")
            print("   2. LLM prioritizing other context over sender_history")
            print("   3. Need to emphasize sender_history more in prompt template")
            return True
        else:
            print("\n⚠️  ISSUES FOUND - Review failed checks above")
            return False


async def main():
    """Run debug script."""
    try:
        success = await debug_sender_history_in_prompt()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Script failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
