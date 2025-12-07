#!/usr/bin/env python3
"""Test script to verify classification improvements for email requiring response.

This script tests the new retry logic and rule-based fallback for email_id=4 scenario.
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.classification import _rule_based_needs_response


def test_rule_based_detection():
    """Test rule-based needs_response detection on email_id=4 content."""

    # Email from email_id=4 that was misclassified
    test_cases = [
        {
            "name": "Email ID=4 (Требует ответ - вопрос 'когда')",
            "subject": "Re: Праздники",
            "body": "Ты не ответил когда сможешь точно сказать о том ждать тебя или нет",
            "expected": True  # Should detect needs_response
        },
        {
            "name": "Email с вопросительным знаком",
            "subject": "Встреча",
            "body": "Ты придешь на встречу завтра?",
            "expected": True
        },
        {
            "name": "Email с императивным глаголом",
            "subject": "Документы",
            "body": "Подтверди получение документов",
            "expected": True
        },
        {
            "name": "Email без вопроса (информация)",
            "subject": "Отчет",
            "body": "Прикрепляю отчет за месяц. Спасибо.",
            "expected": False
        },
        {
            "name": "Email с вопросительным словом 'где'",
            "subject": "Локация",
            "body": "Где будет проходить мероприятие",
            "expected": True
        },
        {
            "name": "Email с вопросительным словом 'почему'",
            "subject": "Вопрос",
            "body": "Почему изменились условия контракта",
            "expected": True
        },
        {
            "name": "Email с модальным глаголом 'можешь'",
            "subject": "Помощь",
            "body": "Можешь помочь с презентацией",
            "expected": True
        }
    ]

    print("=" * 80)
    print("ТЕСТ: Rule-based needs_response detection")
    print("=" * 80)
    print()

    passed = 0
    failed = 0

    for test_case in test_cases:
        result = _rule_based_needs_response(
            email_body=test_case["body"],
            subject=test_case["subject"]
        )

        status = "✅ PASS" if result == test_case["expected"] else "❌ FAIL"

        if result == test_case["expected"]:
            passed += 1
        else:
            failed += 1

        print(f"{status} - {test_case['name']}")
        print(f"   Subject: {test_case['subject']}")
        print(f"   Body: {test_case['body'][:80]}...")
        print(f"   Expected: {test_case['expected']}, Got: {result}")
        print()

    print("=" * 80)
    print(f"РЕЗУЛЬТАТЫ: {passed} passed, {failed} failed из {len(test_cases)} тестов")
    print("=" * 80)
    print()

    return failed == 0


if __name__ == "__main__":
    success = test_rule_based_detection()
    sys.exit(0 if success else 1)
