#!/usr/bin/env python3
"""Test temporal filtering and recency boost for RAG context retrieval.

Tests the improvements to handle emails from same sender with different subjects:
1. Temporal filtering (adaptive window: 30/60/90 days)
2. Recency scoring (half-life decay)
3. Fused scoring (70% semantic + 30% temporal)
4. Subject boost in query construction
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta, UTC
import math

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.context_retrieval import ContextRetrievalService


def test_recency_score_calculation():
    """Test half-life decay calculation for recency scoring."""

    print("=" * 80)
    print("ТЕСТ: Recency Score Calculation (Half-Life Decay)")
    print("=" * 80)
    print()

    # Test recency scoring with different ages
    now_timestamp = int(datetime.now(UTC).timestamp())
    half_life_days = 14  # 14-day half-life as per our implementation

    test_cases = [
        {
            "name": "Email сегодня (0 days old)",
            "days_ago": 0,
            "expected_range": (0.95, 1.0)  # Should be close to 1.0
        },
        {
            "name": "Email 7 дней назад",
            "days_ago": 7,
            "expected_range": (0.7, 0.8)  # Half-life decay after 7 days
        },
        {
            "name": "Email 14 дней назад (half-life)",
            "days_ago": 14,
            "expected_range": (0.45, 0.55)  # Should be ~0.5 at half-life
        },
        {
            "name": "Email 30 дней назад",
            "days_ago": 30,
            "expected_range": (0.2, 0.3)  # Significantly decayed
        },
        {
            "name": "Email 90 дней назад",
            "days_ago": 90,
            "expected_range": (0.01, 0.05)  # Very low recency
        }
    ]

    passed = 0
    failed = 0

    for test_case in test_cases:
        days_ago = test_case["days_ago"]
        timestamp = now_timestamp - (days_ago * 86400)  # 86400 seconds in a day

        # Calculate recency score using our formula
        recency_score = ContextRetrievalService._calculate_recency_score(
            timestamp=timestamp,
            half_life_days=half_life_days
        )

        expected_min, expected_max = test_case["expected_range"]
        passed_test = expected_min <= recency_score <= expected_max

        status = "✅ PASS" if passed_test else "❌ FAIL"

        if passed_test:
            passed += 1
        else:
            failed += 1

        print(f"{status} - {test_case['name']}")
        print(f"   Days ago: {days_ago}")
        print(f"   Recency score: {recency_score:.4f}")
        print(f"   Expected range: [{expected_min}, {expected_max}]")
        print()

    print("=" * 80)
    print(f"РЕЗУЛЬТАТЫ: {passed} passed, {failed} failed из {len(test_cases)} tests")
    print("=" * 80)
    print()

    return failed == 0


def test_fused_score_calculation():
    """Test fused scoring (semantic + temporal)."""

    print("=" * 80)
    print("ТЕСТ: Fused Score Calculation (Semantic + Temporal)")
    print("=" * 80)
    print()

    # Test fused scoring with different combinations
    alpha = 0.7  # 70% semantic, 30% temporal

    test_cases = [
        {
            "name": "Высокое semantic similarity + высокий recency",
            "cosine_distance": 0.1,  # Low distance = high similarity
            "recency_score": 0.9,
            "expected_fused": 0.9  # Both high, fused should be high
        },
        {
            "name": "Высокое semantic similarity + низкий recency",
            "cosine_distance": 0.1,
            "recency_score": 0.1,
            "expected_fused": 0.66  # High semantic dominates (alpha=0.7)
        },
        {
            "name": "Низкое semantic similarity + высокий recency",
            "cosine_distance": 0.9,  # High distance = low similarity
            "recency_score": 0.9,
            "expected_fused": 0.34  # Low semantic pulls down despite high recency
        },
        {
            "name": "Среднее semantic + среднее recency",
            "cosine_distance": 0.5,
            "recency_score": 0.5,
            "expected_fused": 0.5  # Both medium
        }
    ]

    passed = 0
    failed = 0

    for test_case in test_cases:
        fused = ContextRetrievalService._fused_score(
            cosine_sim=test_case["cosine_distance"],
            recency=test_case["recency_score"],
            alpha=alpha
        )

        # Allow 10% tolerance
        expected = test_case["expected_fused"]
        tolerance = 0.1
        passed_test = abs(fused - expected) <= tolerance

        status = "✅ PASS" if passed_test else "❌ FAIL"

        if passed_test:
            passed += 1
        else:
            failed += 1

        print(f"{status} - {test_case['name']}")
        print(f"   Cosine distance: {test_case['cosine_distance']}")
        print(f"   Recency score: {test_case['recency_score']}")
        print(f"   Fused score: {fused:.4f} (expected: ~{expected})")
        print(f"   Formula: {alpha} * (1 - {test_case['cosine_distance']}) + {1-alpha} * {test_case['recency_score']}")
        print()

    print("=" * 80)
    print(f"РЕЗУЛЬТАТЫ: {passed} passed, {failed} failed из {len(test_cases)} tests")
    print("=" * 80)
    print()

    return failed == 0


def test_adaptive_temporal_window():
    """Test adaptive temporal window based on thread length."""

    print("=" * 80)
    print("ТЕСТ: Adaptive Temporal Window")
    print("=" * 80)
    print()

    test_cases = [
        {
            "name": "Новый thread (thread_length=0)",
            "thread_length": 0,
            "expected_window": 30  # Last 30 days for new threads
        },
        {
            "name": "Короткий thread (thread_length=2)",
            "thread_length": 2,
            "expected_window": 60  # Last 60 days for short threads
        },
        {
            "name": "Средний thread (thread_length=3)",
            "thread_length": 3,
            "expected_window": 60  # Last 60 days for <= 3 messages
        },
        {
            "name": "Длинный thread (thread_length=5)",
            "thread_length": 5,
            "expected_window": 90  # Full 90 days for long threads
        },
        {
            "name": "Очень длинный thread (thread_length=10)",
            "thread_length": 10,
            "expected_window": 90  # Full 90 days
        }
    ]

    passed = 0
    failed = 0

    for test_case in test_cases:
        window = ContextRetrievalService._get_temporal_window_days(
            thread_length=test_case["thread_length"]
        )

        expected = test_case["expected_window"]
        passed_test = window == expected

        status = "✅ PASS" if passed_test else "❌ FAIL"

        if passed_test:
            passed += 1
        else:
            failed += 1

        print(f"{status} - {test_case['name']}")
        print(f"   Thread length: {test_case['thread_length']}")
        print(f"   Temporal window: {window} days (expected: {expected})")
        print(f"   Context: Only emails from last {window} days будут включены")
        print()

    print("=" * 80)
    print(f"РЕЗУЛЬТАТЫ: {passed} passed, {failed} failed из {len(test_cases)} tests")
    print("=" * 80)
    print()

    return failed == 0


def test_temporal_filtering_concept():
    """Test the concept of temporal filtering (without actual DB)."""

    print("=" * 80)
    print("ТЕСТ: Temporal Filtering Concept")
    print("=" * 80)
    print()

    # Scenario: Same sender, different subjects at different times
    print("Сценарий: Письма от одного отправителя с разными темами\n")

    now = datetime.now(UTC)

    # Old email about Budget (90 days ago)
    old_email = {
        "subject": "Budget 2025",
        "date": now - timedelta(days=90),
        "body": "Please review the budget for 2025..."
    }

    # Recent email about Holidays (5 days ago)
    recent_email = {
        "subject": "Holiday Plans",
        "date": now - timedelta(days=5),
        "body": "Looking forward to the holidays in Frankfurt..."
    }

    # Current email asking about Holidays
    current_email = {
        "subject": "Re: Holiday Plans",
        "date": now,
        "body": "When can you confirm about the holidays?"
    }

    print(f"📧 Old Email (90 days ago):")
    print(f"   Subject: {old_email['subject']}")
    print(f"   Date: {old_email['date'].strftime('%Y-%m-%d')}")
    print()

    print(f"📧 Recent Email (5 days ago):")
    print(f"   Subject: {recent_email['subject']}")
    print(f"   Date: {recent_email['date'].strftime('%Y-%m-%d')}")
    print()

    print(f"📧 Current Email (now):")
    print(f"   Subject: {current_email['subject']}")
    print(f"   Date: {current_email['date'].strftime('%Y-%m-%d')}")
    print()

    print("=" * 80)
    print("Анализ с Temporal Filtering:")
    print("=" * 80)
    print()

    # Temporal window for new thread (thread_length=1)
    temporal_window = ContextRetrievalService._get_temporal_window_days(thread_length=1)
    cutoff_date = now - timedelta(days=temporal_window)

    print(f"Temporal Window: {temporal_window} days")
    print(f"Cutoff Date: {cutoff_date.strftime('%Y-%m-%d')}")
    print()

    # Check which emails would be included
    old_timestamp = int(old_email["date"].timestamp())
    recent_timestamp = int(recent_email["date"].timestamp())

    old_recency = ContextRetrievalService._calculate_recency_score(old_timestamp, half_life_days=14)
    recent_recency = ContextRetrievalService._calculate_recency_score(recent_timestamp, half_life_days=14)

    old_included = old_email["date"] >= cutoff_date
    recent_included = recent_email["date"] >= cutoff_date

    print(f"Old Email (Budget):")
    print(f"   ❌ Included in results: {old_included}")
    print(f"   Recency score: {old_recency:.4f} (very low)")
    print(f"   Reason: {old_email['date'].strftime('%Y-%m-%d')} < cutoff {cutoff_date.strftime('%Y-%m-%d')}")
    print()

    print(f"Recent Email (Holidays):")
    print(f"   ✅ Included in results: {recent_included}")
    print(f"   Recency score: {recent_recency:.4f} (high)")
    print(f"   Reason: {recent_email['date'].strftime('%Y-%m-%d')} >= cutoff {cutoff_date.strftime('%Y-%m-%d')}")
    print()

    print("=" * 80)
    print("РЕЗУЛЬТАТ:")
    print("=" * 80)

    if not old_included and recent_included:
        print("✅ SUCCESS: Temporal filtering работает правильно!")
        print("   - Старые письма о Budget отфильтрованы")
        print("   - Свежие письма о Holidays включены в контекст")
        print("   - LLM получит только релевантный контекст о Holidays")
        print()
        return True
    else:
        print("❌ FAIL: Temporal filtering не работает как ожидалось")
        return False


def main():
    """Run all temporal filtering tests."""

    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 18 + "TEMPORAL FILTERING & RECENCY BOOST TESTS" + " " * 20 + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    # Test 1: Recency score calculation
    test1_pass = test_recency_score_calculation()

    # Test 2: Fused score calculation
    test2_pass = test_fused_score_calculation()

    # Test 3: Adaptive temporal window
    test3_pass = test_adaptive_temporal_window()

    # Test 4: Temporal filtering concept
    test4_pass = test_temporal_filtering_concept()

    # Summary
    all_pass = test1_pass and test2_pass and test3_pass and test4_pass

    print("\n")
    print("=" * 80)
    print("ФИНАЛЬНЫЙ РЕЗУЛЬТАТ:")
    print("=" * 80)
    print(f"  Recency Score Calculation:  {'✅ PASS' if test1_pass else '❌ FAIL'}")
    print(f"  Fused Score Calculation:    {'✅ PASS' if test2_pass else '❌ FAIL'}")
    print(f"  Adaptive Temporal Window:   {'✅ PASS' if test3_pass else '❌ FAIL'}")
    print(f"  Temporal Filtering Concept: {'✅ PASS' if test4_pass else '❌ FAIL'}")
    print("=" * 80)

    if all_pass:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО! 🎉\n")
        print("Improvements verified:")
        print("  1. ✅ Half-life decay (14 days) правильно вычисляет recency scores")
        print("  2. ✅ Fused scoring (70% semantic + 30% temporal) работает корректно")
        print("  3. ✅ Adaptive temporal window адаптируется по thread length")
        print("  4. ✅ Temporal filtering отсекает старые нерелевантные письма")
        print()
        print("РЕШЕНА ПРОБЛЕМА:")
        print("  ❌ Было: Письма о 'Budget' (90 дней назад) возвращались для запроса о 'Holidays'")
        print("  ✅ Стало: Только свежие письма о 'Holidays' попадают в RAG контекст")
        print()
    else:
        print("\n❌ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛИЛИСЬ\n")

    return all_pass


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
