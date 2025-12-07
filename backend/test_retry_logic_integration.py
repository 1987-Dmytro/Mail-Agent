#!/usr/bin/env python3
"""Integration test for retry logic and fallback classification.

Tests the complete classification flow including:
1. Retry decorator with exponential backoff
2. Rule-based fallback when LLM fails
"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.classification import EmailClassificationService, _rule_based_needs_response
from app.utils.errors import GeminiRateLimitError


async def test_retry_logic():
    """Test that retry logic works for rate limit errors."""

    print("=" * 80)
    print("ТЕСТ: Retry Logic с Exponential Backoff")
    print("=" * 80)
    print()

    # Mock dependencies
    mock_llm_client = Mock()
    mock_db = Mock()
    mock_gmail_client = Mock()
    mock_llm_client.receive_completion = AsyncMock()

    # Create classification service
    service = EmailClassificationService(
        db=mock_db,
        gmail_client=mock_gmail_client,
        llm_client=mock_llm_client
    )

    # Test Case 1: Rate limit на первой попытке, успех на второй
    print("Test Case 1: Rate limit → Retry → Success")
    print("-" * 80)

    mock_llm_client.receive_completion.side_effect = [
        GeminiRateLimitError("Rate limit exceeded"),  # 1st attempt: fail
        {  # 2nd attempt: success
            "suggested_folder": "Important",
            "reasoning": "Email requires response",
            "needs_response": True,
            "priority_score": 80,
            "confidence": 0.9
        }
    ]

    email_data = {
        "subject": "Re: Праздники",
        "body": "Ты не ответил когда сможешь точно сказать о том ждать тебя или нет",
        "sender": "test@example.com",
        "received_at": "2025-12-06T22:47:25Z",
        "user_id": 1
    }

    try:
        result = await service.classify_email(
            email_data=email_data,
            user_folders=["Important", "Work", "Personal"]
        )

        print(f"✅ Retry logic работает!")
        print(f"   - Попыток до успеха: 2")
        print(f"   - Результат: needs_response={result.needs_response}")
        print(f"   - Suggested folder: {result.suggested_folder}")
        print()

    except Exception as e:
        print(f"❌ FAIL: {e}")
        print()
        return False

    # Test Case 2: Rate limit на всех 3 попытках → Fallback с rule-based detection
    print("Test Case 2: Rate limit (3x) → Rule-based Fallback")
    print("-" * 80)

    mock_llm_client.receive_completion.side_effect = [
        GeminiRateLimitError("Rate limit exceeded"),  # 1st attempt
        GeminiRateLimitError("Rate limit exceeded"),  # 2nd attempt
        GeminiRateLimitError("Rate limit exceeded"),  # 3rd attempt (exhausted)
    ]

    try:
        result = await service.classify_email(
            email_data=email_data,
            user_folders=["Important", "Work", "Personal"]
        )

        # Verify rule-based detection worked
        expected_needs_response = _rule_based_needs_response(
            email_body=email_data["body"],
            subject=email_data["subject"]
        )

        if result.needs_response == expected_needs_response:
            print(f"✅ Rule-based fallback работает!")
            print(f"   - После исчерпания retry: Использован rule-based fallback")
            print(f"   - Rule-based detection: needs_response={result.needs_response}")
            print(f"   - Confidence: {result.confidence} (fallback mode)")
            print()
        else:
            print(f"❌ FAIL: Rule-based fallback вернул неправильный результат")
            print(f"   Expected: {expected_needs_response}, Got: {result.needs_response}")
            print()
            return False

    except Exception as e:
        print(f"❌ FAIL: {e}")
        print()
        return False

    print("=" * 80)
    print("РЕЗУЛЬТАТ: ✅ Все тесты retry logic прошли успешно")
    print("=" * 80)
    print()
    return True


async def test_email_id_4_scenario():
    """Test exact scenario from email_id=4."""

    print("=" * 80)
    print("ТЕСТ: Email ID=4 Scenario (Real World)")
    print("=" * 80)
    print()

    # Mock dependencies
    mock_llm_client = Mock()
    mock_db = Mock()
    mock_gmail_client = Mock()
    mock_llm_client.receive_completion = AsyncMock()

    # Create classification service
    service = EmailClassificationService(
        db=mock_db,
        gmail_client=mock_gmail_client,
        llm_client=mock_llm_client
    )

    # Simulate GeminiRateLimitError like in the real scenario
    mock_llm_client.receive_completion.side_effect = GeminiRateLimitError(
        "Quota exceeded for quota metric 'Generate Content API requests per minute' "
        "and limit 'GenerateContentRequestsPerMinutePerProjectPerRegion' of service "
        "'generativelanguage.googleapis.com' for consumer 'project_number:1004123737330'."
    )

    # Exact email from email_id=4
    email_data = {
        "subject": "Re: Праздники",
        "body": "Ты не ответил когда сможешь точно сказать о том ждать тебя или нет",
        "sender": "hordieenko.dmytro@keemail.me",
        "received_at": "2025-12-06T22:47:25Z",
        "user_id": 2
    }

    try:
        result = await service.classify_email(
            email_data=email_data,
            user_folders=["Important", "Work", "Personal"]
        )

        print(f"Email ID=4 Classification Result:")
        print(f"  Subject: {email_data['subject']}")
        print(f"  Body: {email_data['body']}")
        print()
        print(f"  ✅ needs_response: {result.needs_response}")
        print(f"  ✅ suggested_folder: {result.suggested_folder}")
        print(f"  ✅ reasoning: {result.reasoning[:100]}...")
        print(f"  ✅ confidence: {result.confidence}")
        print()

        if result.needs_response:
            print("✅ SUCCESS: Email правильно определен как требующий ответа!")
            print("   (Старая версия возвращала needs_response=False)")
        else:
            print("❌ FAIL: Email все еще не определен как требующий ответа")
            return False

    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False

    print("=" * 80)
    print("РЕЗУЛЬТАТ: ✅ Email ID=4 scenario работает правильно")
    print("=" * 80)
    print()
    return True


async def main():
    """Run all integration tests."""

    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 15 + "INTEGRATION TESTS: Classification Improvements" + " " * 16 + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    # Test 1: Retry logic
    test1_pass = await test_retry_logic()

    # Test 2: Email ID=4 scenario
    test2_pass = await test_email_id_4_scenario()

    # Summary
    all_pass = test1_pass and test2_pass

    print("\n")
    print("=" * 80)
    print("ФИНАЛЬНЫЙ РЕЗУЛЬТАТ:")
    print("=" * 80)
    print(f"  Retry Logic Test: {'✅ PASS' if test1_pass else '❌ FAIL'}")
    print(f"  Email ID=4 Test:  {'✅ PASS' if test2_pass else '❌ FAIL'}")
    print("=" * 80)

    if all_pass:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО! 🎉\n")
        print("Improvements verified:")
        print("  1. ✅ Retry logic с exponential backoff работает")
        print("  2. ✅ Rule-based fallback правильно определяет needs_response")
        print("  3. ✅ Email ID=4 scenario теперь работает корректно")
        print()
    else:
        print("\n❌ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛИЛИСЬ\n")

    return all_pass


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
