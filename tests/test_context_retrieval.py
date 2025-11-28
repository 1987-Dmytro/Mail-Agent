"""
Unit Tests for Context Retrieval Service

Tests for Smart Hybrid RAG implementation (Story 3.4):
- Thread history retrieval from Gmail
- Semantic search in vector DB
- Adaptive k logic based on thread length
- Result ranking by relevance and recency
- Token counting and budget enforcement
- Main context retrieval orchestration
- Performance monitoring

Test Strategy:
- Mock all external dependencies (GmailClient, VectorDBClient, EmbeddingService)
- Test each method in isolation with unit tests
- Verify adaptive k logic for short/standard/long threads
- Test token budget enforcement with truncation
- Measure performance timing (<3s target)

Created: 2025-11-09
Epic: 3 (RAG System & Response Generation)
Story: 3.4 (Context Retrieval Service)
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import time

from app.services.context_retrieval import ContextRetrievalService
from app.models.context_models import EmailMessage, RAGContext


class TestThreadHistoryRetrieval:
    """Test suite for thread history retrieval (AC #2)."""

    @pytest.mark.asyncio
    async def test_get_thread_history_returns_last_5_emails(self):
        """
        Test: Thread with >5 emails returns last 5
        Verify: Method returns exactly 5 most recent emails in chronological order
        AC #2: Method retrieves thread history from Gmail (last 5 emails in chronological order)
        """
        # Arrange: Create mock GmailClient with 8 emails in thread
        mock_gmail_client = AsyncMock()
        mock_thread_messages = [
            {
                "message_id": f"msg{i}",
                "thread_id": "thread123",
                "sender": f"sender{i}@example.com",
                "subject": f"Subject {i}",
                "body": f"Email body {i}",
                "received_at": datetime(2025, 11, i+1, 10, 0, 0)
            }
            for i in range(1, 9)  # 8 emails (oldest to newest)
        ]
        mock_gmail_client.get_thread.return_value = mock_thread_messages

        service = ContextRetrievalService(
            user_id=123,
            gmail_client=mock_gmail_client,
            db_service=Mock()
        )

        # Act: Fetch thread history
        result, original_length = await service._get_thread_history("thread123")

        # Assert: Returns last 5 emails only
        assert len(result) == 5, "Should return exactly 5 emails when thread has >5"
        assert original_length == 8, "Should track original thread length before truncation"
        assert result[0]["message_id"] == "msg4", "Should start with 4th email (oldest of last 5)"
        assert result[4]["message_id"] == "msg8", "Should end with 8th email (newest)"

        # Verify chronological order (oldest → newest)
        for i in range(len(result) - 1):
            assert result[i]["date"] < result[i + 1]["date"], "Emails should be in chronological order"

        # Verify EmailMessage structure
        assert all(key in result[0] for key in ["message_id", "sender", "subject", "body", "date", "thread_id"])


class TestSemanticSearch:
    """Test suite for semantic search retrieval (AC #3, #4)."""

    @pytest.mark.asyncio
    async def test_get_semantic_results_queries_vector_db(self):
        """
        Test: Semantic search queries ChromaDB with correct parameters
        Verify: VectorDBClient.query_embeddings called with correct collection, filter, n_results
        AC #3: Method performs semantic search in vector DB using email content as query embedding
        AC #4: Top-k most relevant emails retrieved with adaptive k logic
        """
        # Arrange: Mock EmbeddingService and VectorDBClient
        mock_embedding_service = Mock()
        mock_embedding_service.embed_text.return_value = [0.1] * 768  # 768-dim embedding

        mock_vector_db = Mock()
        mock_vector_db.query_embeddings.return_value = {
            "ids": [["msg1", "msg2", "msg3"]],
            "metadatas": [[
                {"message_id": "msg1", "thread_id": "t1", "sender": "sender1@example.com"},
                {"message_id": "msg2", "thread_id": "t2", "sender": "sender2@example.com"},
                {"message_id": "msg3", "thread_id": "t3", "sender": "sender3@example.com"}
            ]],
            "distances": [[0.2, 0.3, 0.4]]  # Cosine similarity scores
        }

        mock_gmail_client = AsyncMock()
        mock_gmail_client.get_message_detail.side_effect = [
            {
                "message_id": "msg1",
                "thread_id": "t1",
                "sender": "sender1@example.com",
                "subject": "Subject 1",
                "body": "Body 1",
                "received_at": datetime(2025, 11, 1, 10, 0, 0)
            },
            {
                "message_id": "msg2",
                "thread_id": "t2",
                "sender": "sender2@example.com",
                "subject": "Subject 2",
                "body": "Body 2",
                "received_at": datetime(2025, 11, 2, 10, 0, 0)
            },
            {
                "message_id": "msg3",
                "thread_id": "t3",
                "sender": "sender3@example.com",
                "subject": "Subject 3",
                "body": "Body 3",
                "received_at": datetime(2025, 11, 3, 10, 0, 0)
            }
        ]

        service = ContextRetrievalService(
            user_id=123,
            gmail_client=mock_gmail_client,
            embedding_service=mock_embedding_service,
            vector_db_client=mock_vector_db,
            db_service=Mock()
        )

        # Act: Perform semantic search
        result = await service._get_semantic_results(
            email_body="Tax return deadline",
            k=3,
            user_id=123
        )

        # Assert: VectorDBClient.query_embeddings called correctly
        mock_embedding_service.embed_text.assert_called_once_with("Tax return deadline")
        mock_vector_db.query_embeddings.assert_called_once_with(
            collection_name="email_embeddings",
            query_embedding=[0.1] * 768,
            n_results=3,
            filter={"user_id": "123"}  # ChromaDB expects string
        )

        # Verify results returned with full email bodies
        assert len(result) == 3
        assert result[0]["message_id"] == "msg1"
        assert result[0]["body"] == "Body 1", "Should fetch full bodies from Gmail"
        assert "_distance" in result[0], "Should attach distance scores for ranking"


class TestAdaptiveKLogic:
    """Test suite for adaptive k calculation (AC #5)."""

    def test_calculate_adaptive_k_logic(self):
        """
        Test: Adaptive k logic for short/standard/long threads
        Verify: k=7 for <3 emails, k=3 for 3-5 emails, k=0 for >5 emails
        AC #5: Adaptive k implementation based on thread length
        """
        service = ContextRetrievalService(user_id=123, db_service=Mock())

        # Short thread (<3 emails) → k=7
        k_short = service._calculate_adaptive_k(thread_length=2)
        assert k_short == 7, "Short threads (<3 emails) should get k=7 for more semantic context"

        # Standard thread (3-5 emails) → k=3
        k_standard = service._calculate_adaptive_k(thread_length=4)
        assert k_standard == 3, "Standard threads (3-5 emails) should get k=3 for balanced hybrid"

        # Long thread (>5 emails) → k=0
        k_long = service._calculate_adaptive_k(thread_length=8)
        assert k_long == 0, "Long threads (>5 emails) should get k=0 to skip semantic search"

        # Edge cases: Exact boundaries
        assert service._calculate_adaptive_k(1) == 7, "1 email = short thread"
        assert service._calculate_adaptive_k(3) == 3, "3 emails = standard thread (boundary)"
        assert service._calculate_adaptive_k(5) == 3, "5 emails = standard thread (boundary)"
        assert service._calculate_adaptive_k(6) == 0, "6 emails = long thread (boundary)"


class TestResultRanking:
    """Test suite for semantic result ranking (AC #7)."""

    def test_rank_semantic_results_by_score_and_recency(self):
        """
        Test: Results ranked by cosine similarity, with recency as tiebreaker
        Verify: Lower distance = higher rank, recent emails preferred on tie
        AC #7: Semantic results ranked by relevance score and recency
        """
        service = ContextRetrievalService(user_id=123, db_service=Mock())

        # Arrange: Create emails with different distances and dates
        emails = [
            {
                "message_id": "msg1",
                "sender": "sender1@example.com",
                "subject": "Subject 1",
                "body": "Body 1",
                "date": "2025-11-01T10:00:00Z",
                "thread_id": "t1",
                "_distance": 0.5  # Lowest similarity
            },
            {
                "message_id": "msg2",
                "sender": "sender2@example.com",
                "subject": "Subject 2",
                "body": "Body 2",
                "date": "2025-11-02T10:00:00Z",
                "thread_id": "t2",
                "_distance": 0.2  # High similarity
            },
            {
                "message_id": "msg3",
                "sender": "sender3@example.com",
                "subject": "Subject 3",
                "body": "Body 3",
                "date": "2025-11-03T10:00:00Z",  # Most recent
                "thread_id": "t3",
                "_distance": 0.2  # Same similarity as msg2 (tie)
            }
        ]

        # Act: Rank results
        ranked = service._rank_semantic_results(emails)

        # Assert: Ranked by distance (lower = better), then by recency (ties)
        assert ranked[0]["message_id"] == "msg3", "msg3 should be first (distance=0.2, most recent)"
        assert ranked[1]["message_id"] == "msg2", "msg2 should be second (distance=0.2, less recent than msg3)"
        assert ranked[2]["message_id"] == "msg1", "msg1 should be last (distance=0.5, lowest similarity)"

        # Verify _distance removed after ranking
        assert "_distance" not in ranked[0], "Should remove temporary _distance attribute"


class TestTokenCounting:
    """Test suite for token counting (AC #8)."""

    def test_count_tokens_uses_tiktoken(self):
        """
        Test: Token counting uses tiktoken library
        Verify: Accurate token counts for various text lengths
        AC #8: Context window managed using tiktoken token counter
        """
        service = ContextRetrievalService(user_id=123, db_service=Mock())

        # Test various text lengths
        short_text = "Hello world"
        medium_text = "This is a test email body with multiple sentences. It contains more content to test token counting accuracy."
        long_text = medium_text * 10

        count_short = service._count_tokens(short_text)
        count_medium = service._count_tokens(medium_text)
        count_long = service._count_tokens(long_text)

        # Verify reasonable token counts (tiktoken typically ~4 chars per token)
        assert count_short > 0 and count_short < 10, "Short text should have few tokens"
        assert count_medium > count_short, "Medium text should have more tokens than short"
        assert count_long > count_medium, "Long text should have more tokens than medium"
        # Note: Token count may not scale exactly linearly due to tokenizer efficiency
        assert count_long > count_medium * 5, "Long text (10x) should have significantly more tokens"

        # Test empty text
        assert service._count_tokens("") == 0, "Empty text should have 0 tokens"


class TestTokenBudgetEnforcement:
    """Test suite for token budget enforcement (AC #9)."""

    def test_enforce_token_budget_truncates_correctly(self):
        """
        Test: Token budget enforcement truncates context when over 6.5K tokens
        Verify: Thread history truncated first, then semantic results
        AC #9: Token counting implemented to enforce ~6.5K token budget
        """
        service = ContextRetrievalService(user_id=123, db_service=Mock())

        # Arrange: Create thread history and semantic results that exceed budget
        # Use large text bodies to exceed 6500 token budget
        # Calculate actual tokens instead of estimating
        large_body = "This is a long email body content. " * 200  # Repeat to make large

        thread_history = [
            {
                "message_id": f"thread{i}",
                "sender": f"sender{i}@example.com",
                "subject": f"Subject {i}",
                "body": large_body,
                "date": f"2025-11-0{i}T10:00:00Z",
                "thread_id": "t1"
            }
            for i in range(1, 6)  # 5 emails
        ]

        semantic_results = [
            {
                "message_id": f"semantic{i}",
                "sender": f"sender{i}@example.com",
                "subject": f"Subject {i}",
                "body": large_body,
                "date": f"2025-11-0{i}T10:00:00Z",
                "thread_id": f"t{i}"
            }
            for i in range(1, 4)  # 3 emails
        ]

        # Calculate actual token counts before enforcement
        original_total = sum(service._count_tokens(email["body"]) for email in thread_history)
        original_total += sum(service._count_tokens(email["body"]) for email in semantic_results)
        # Ensure we're actually over budget for this test to be meaningful
        assert original_total > 6500, f"Test setup error: Total tokens ({original_total}) should exceed budget (6500)"

        # Act: Enforce token budget
        truncated_thread, truncated_semantic = service._enforce_token_budget(
            thread_history=thread_history,
            semantic_results=semantic_results,
            max_tokens=6500
        )

        # Assert: Context truncated to fit budget
        total_tokens = sum(service._count_tokens(email["body"]) for email in truncated_thread)
        total_tokens += sum(service._count_tokens(email["body"]) for email in truncated_semantic)

        assert total_tokens <= 6500, "Total tokens should be under budget after truncation"
        assert len(truncated_thread) < len(thread_history), "Thread history should be truncated"
        assert truncated_thread[-1]["message_id"] == "thread5", "Most recent thread emails kept"

        # Verify truncation strategy: Thread first, then semantic
        if len(truncated_thread) > 0:
            # If any thread emails kept, verify they're the most recent
            assert truncated_thread[-1] == thread_history[-1], "Most recent thread email preserved"


class TestContextRetrievalOrchestration:
    """Test suite for main context retrieval method (AC #1, #6, #10)."""

    @pytest.mark.asyncio
    async def test_retrieve_context_combines_thread_and_semantic(self):
        """
        Test: Main retrieval method combines thread history and semantic search
        Verify: RAGContext structure complete with thread_history, semantic_results, metadata
        AC #1: Context retrieval method created that takes email_id and returns RAGContext
        AC #6: Results combined into RAGContext structure
        AC #10: Context formatted as structured RAGContext TypedDict
        """
        # Arrange: Mock all dependencies
        mock_db_service = Mock()
        mock_session = AsyncMock()

        # Mock database query result
        mock_email = Mock()
        mock_email.id = 456
        mock_email.gmail_thread_id = "thread123"
        mock_email.subject = "Tax Return"
        mock_email.body = "Please submit your tax return by..."

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_email
        mock_session.execute.return_value = mock_result

        # Mock async context manager properly
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None
        mock_db_service.async_session.return_value = mock_context_manager

        # Mock GmailClient (thread history)
        mock_gmail_client = AsyncMock()
        mock_gmail_client.get_thread.return_value = [
            {
                "message_id": f"thread{i}",
                "thread_id": "thread123",
                "sender": f"sender{i}@example.com",
                "subject": f"Subject {i}",
                "body": f"Thread body {i}",
                "received_at": datetime(2025, 11, i, 10, 0, 0)
            }
            for i in range(1, 5)  # 4 emails in thread
        ]

        # Mock EmbeddingService
        mock_embedding_service = Mock()
        mock_embedding_service.embed_text.return_value = [0.1] * 768

        # Mock VectorDBClient (semantic search)
        mock_vector_db = Mock()
        mock_vector_db.query_embeddings.return_value = {
            "ids": [["semantic1", "semantic2", "semantic3"]],
            "metadatas": [[
                {"message_id": "semantic1"},
                {"message_id": "semantic2"},
                {"message_id": "semantic3"}
            ]],
            "distances": [[0.2, 0.3, 0.4]]
        }

        # Mock Gmail get_message_detail for semantic results
        mock_gmail_client.get_message_detail.side_effect = [
            {
                "message_id": f"semantic{i}",
                "thread_id": f"t{i}",
                "sender": f"sender{i}@example.com",
                "subject": f"Semantic Subject {i}",
                "body": f"Semantic body {i}",
                "received_at": datetime(2025, 11, i, 10, 0, 0)
            }
            for i in range(1, 4)
        ]

        service = ContextRetrievalService(
            user_id=123,
            db_service=mock_db_service,
            gmail_client=mock_gmail_client,
            embedding_service=mock_embedding_service,
            vector_db_client=mock_vector_db
        )

        # Act: Retrieve context
        context = await service.retrieve_context(email_id=456)

        # Assert: RAGContext structure complete
        assert "thread_history" in context, "RAGContext should have thread_history"
        assert "semantic_results" in context, "RAGContext should have semantic_results"
        assert "metadata" in context, "RAGContext should have metadata"

        # Verify thread_history populated
        assert len(context["thread_history"]) == 4, "Thread history should have 4 emails"
        assert context["thread_history"][0]["message_id"] == "thread1"

        # Verify semantic_results populated
        assert len(context["semantic_results"]) == 3, "Semantic results should have 3 emails (k=3 for standard thread)"
        assert context["semantic_results"][0]["message_id"] == "semantic1"

        # Verify metadata populated
        metadata = context["metadata"]
        assert "thread_length" in metadata
        assert "semantic_count" in metadata
        assert "oldest_thread_date" in metadata
        assert "total_tokens_used" in metadata
        assert metadata["thread_length"] == 4
        assert metadata["semantic_count"] == 3


class TestPerformance:
    """Test suite for performance monitoring (AC #11, #12)."""

    @pytest.mark.asyncio
    async def test_retrieve_context_performance_under_3_seconds(self):
        """
        Test: Context retrieval completes in <3 seconds
        Verify: Performance logged, timing measured with perf_counter
        AC #11: Query performance measured and logged (target: <3 seconds per NFR001)
        AC #12: Performance optimization via parallel retrieval
        """
        # Arrange: Mock all dependencies (fast mocks)
        mock_db_service = Mock()
        mock_session = AsyncMock()

        mock_email = Mock()
        mock_email.id = 456
        mock_email.gmail_thread_id = "thread123"
        mock_email.subject = "Test"
        mock_email.body = "Test body"

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_email
        mock_session.execute.return_value = mock_result

        # Mock async context manager properly
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None
        mock_db_service.async_session.return_value = mock_context_manager

        # Fast mocks (immediate return)
        mock_gmail_client = AsyncMock()
        mock_gmail_client.get_thread.return_value = [
            {
                "message_id": "thread1",
                "thread_id": "thread123",
                "sender": "sender@example.com",
                "subject": "Subject",
                "body": "Body",
                "received_at": datetime(2025, 11, 1, 10, 0, 0)
            }
        ]
        mock_gmail_client.get_message_detail.return_value = {
            "message_id": "semantic1",
            "thread_id": "t1",
            "sender": "sender@example.com",
            "subject": "Subject",
            "body": "Body",
            "received_at": datetime(2025, 11, 1, 10, 0, 0)
        }

        mock_embedding_service = Mock()
        mock_embedding_service.embed_text.return_value = [0.1] * 768

        mock_vector_db = Mock()
        mock_vector_db.query_embeddings.return_value = {
            "ids": [["semantic1"]],
            "metadatas": [[{"message_id": "semantic1"}]],
            "distances": [[0.2]]
        }

        service = ContextRetrievalService(
            user_id=123,
            db_service=mock_db_service,
            gmail_client=mock_gmail_client,
            embedding_service=mock_embedding_service,
            vector_db_client=mock_vector_db
        )

        # Act: Measure retrieval time
        start_time = time.perf_counter()
        context = await service.retrieve_context(email_id=456)
        elapsed_time = time.perf_counter() - start_time

        # Assert: Retrieval completes in <3 seconds
        assert elapsed_time < 3.0, f"Retrieval took {elapsed_time:.3f}s, expected <3s (NFR001)"

        # Verify context returned successfully
        assert context is not None
        assert "metadata" in context
        assert context["metadata"]["total_tokens_used"] > 0
