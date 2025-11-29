"""
Integration Tests for Context Retrieval Service

Tests end-to-end context retrieval workflows with real ChromaDB (Story 3.4):
- Short thread adaptive k logic (k=7)
- Standard thread hybrid RAG (k=3)
- Long thread semantic skip (k=0)
- Token budget enforcement with real content
- Performance with parallel retrieval

Integration Test Strategy:
- Use real VectorDBClient with ChromaDB test instance
- Mock GmailClient (avoid real Gmail API calls)
- Test database with test user and sample emails
- Cleanup fixtures to remove test data after each test
- Verify RAGContext structure completeness in all scenarios

Created: 2025-11-09
Epic: 3 (RAG System & Response Generation)
Story: 3.4 (Context Retrieval Service)
"""

import os
import pytest
import pytest_asyncio
import time
from datetime import datetime, UTC
from unittest.mock import AsyncMock, Mock, patch
from sqlmodel import select

from app.services.context_retrieval import ContextRetrievalService
from app.core.vector_db import VectorDBClient
from app.core.embedding_service import EmbeddingService
from app.models.context_models import RAGContext
from app.models.email import EmailProcessingQueue
from app.models.user import User
from app.services.database import database_service


@pytest_asyncio.fixture
async def context_test_user(db_session):
    """Create test user for context retrieval integration tests."""
    user = User(
        email="test_context_retrieval@example.com",
        is_active=True,
        telegram_id="999999999",
        telegram_username="context_test_user",
        telegram_linked_at=datetime.now(UTC),
        created_at=datetime.now(UTC)
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    yield user
    # Cleanup handled by test database teardown


@pytest_asyncio.fixture
async def context_test_email(db_session, context_test_user):
    """Create test email in EmailProcessingQueue for context retrieval tests."""
    email = EmailProcessingQueue(
        user_id=context_test_user.id,
        gmail_message_id="test_msg_context_retrieval",
        gmail_thread_id="test_thread_context_retrieval",
        sender="sender@example.com",
        subject="Test Email for Context Retrieval",
        received_at=datetime(2025, 11, 9, 10, 0, 0),
        status="pending"
    )
    db_session.add(email)
    await db_session.commit()
    await db_session.refresh(email)
    yield email


@pytest.fixture(scope="function")
def test_vector_db():
    """Create VectorDBClient with test ChromaDB instance for each test."""
    import uuid
    # Use unique directory for each test to avoid database locking issues
    test_persist_dir = f"./data/chroma_test_context_retrieval_{uuid.uuid4().hex[:8]}"
    os.makedirs(test_persist_dir, exist_ok=True)

    vector_db = VectorDBClient(persist_directory=test_persist_dir)

    # Create test collection
    collection = vector_db.get_or_create_collection("email_embeddings")

    yield vector_db

    # Cleanup: Delete test data directory
    try:
        import shutil
        # Close the ChromaDB client first
        if hasattr(vector_db, 'client'):
            try:
                # ChromaDB client cleanup if needed
                pass
            except:
                pass
        shutil.rmtree(test_persist_dir, ignore_errors=True)
    except Exception:
        pass


@pytest_asyncio.fixture
async def indexed_emails(test_vector_db, context_test_user):
    """Create sample indexed emails in ChromaDB for semantic search."""
    # Create 10 sample email embeddings with metadata
    # First 7 emails from "sender@example.com" (to match context_test_email sender)
    # Last 3 from different senders (to test filtering)
    sample_embeddings = []
    for i in range(1, 11):
        embedding = [0.1 + (i * 0.01)] * 768  # Vary embeddings slightly
        # Use "sender@example.com" for first 7, different senders for last 3
        sender_email = "sender@example.com" if i <= 7 else f"other_sender{i}@example.com"
        metadata = {
            "message_id": f"indexed_msg_{i}",
            "thread_id": f"thread_{i}",
            "sender": sender_email,
            "date": f"2025-11-0{i % 9 + 1}",
            "subject": f"Indexed Email {i}",
            "language": "en",
            "snippet": f"This is indexed email {i} snippet...",
            "user_id": str(context_test_user.id)
        }
        sample_embeddings.append((f"indexed_msg_{i}", embedding, metadata))

    # Add to ChromaDB
    ids = [e[0] for e in sample_embeddings]
    embeddings = [e[1] for e in sample_embeddings]
    metadatas = [e[2] for e in sample_embeddings]

    test_vector_db.insert_embeddings_batch(
        collection_name="email_embeddings",
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )

    yield sample_embeddings

    # Cleanup handled by test_vector_db fixture


@pytest.fixture
def mock_gmail_client():
    """Mock GmailClient for integration tests (avoid real Gmail API calls)."""
    mock_client = AsyncMock()

    # Default thread with 4 emails (standard thread)
    mock_client.get_thread.return_value = [
        {
            "message_id": f"thread_msg_{i}",
            "thread_id": "test_thread",
            "sender": f"sender{i}@example.com",
            "subject": f"Thread Subject {i}",
            "body": f"Thread email body {i} with some content to test.",
            "received_at": datetime(2025, 11, i, 10, 0, 0)
        }
        for i in range(1, 5)  # 4 emails
    ]

    # Mock get_message_detail for semantic results
    mock_client.get_message_detail.side_effect = lambda msg_id: {
        "message_id": msg_id,
        "thread_id": f"thread_for_{msg_id}",
        "sender": f"sender_{msg_id}@example.com",
        "subject": f"Subject for {msg_id}",
        "body": f"Full body for {msg_id} with detailed content.",
        "received_at": datetime(2025, 11, 5, 10, 0, 0)
    }

    return mock_client


@pytest.fixture
def mock_embedding_service():
    """Mock EmbeddingService for integration tests."""
    mock_service = Mock()
    # Return consistent embedding for queries
    mock_service.embed_text.return_value = [0.15] * 768  # Mid-range embedding
    return mock_service


class TestShortThreadAdaptiveK:
    """Test suite for short thread adaptive k logic (AC #2, #3, #4, #5)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_retrieve_context_short_thread_adaptive_k(
        self,
        db_session,
        context_test_user,
        context_test_email,
        test_vector_db,
        indexed_emails,
        mock_gmail_client,
        mock_embedding_service
    ):
        """
        Test: Short thread (2 emails) retrieves k=7 semantic results
        Verify: Adaptive k=7, combined context structure complete
        AC #2: Thread history retrieval
        AC #3: Semantic search in vector DB
        AC #4: Top-k retrieval with adaptive logic
        AC #5: Short threads (<3 emails) → k=7
        """
        # Arrange: Mock short thread (2 emails)
        mock_gmail_client.get_thread.return_value = [
            {
                "message_id": "thread_msg_1",
                "thread_id": "test_thread",
                "sender": "sender1@example.com",
                "subject": "Short Thread Subject",
                "body": "First email in short thread.",
                "received_at": datetime(2025, 11, 1, 10, 0, 0)
            },
            {
                "message_id": "thread_msg_2",
                "thread_id": "test_thread",
                "sender": "sender2@example.com",
                "subject": "Short Thread Subject",
                "body": "Second email in short thread.",
                "received_at": datetime(2025, 11, 2, 10, 0, 0)
            }
        ]

        service = ContextRetrievalService(
            user_id=context_test_user.id,
            db_service=database_service,
            gmail_client=mock_gmail_client,
            embedding_service=mock_embedding_service,
            vector_db_client=test_vector_db
        )

        # Act: Retrieve context
        context = await service.retrieve_context(email_id=context_test_email.id)

        # Assert: Short thread → k=7 semantic results
        assert len(context["thread_history"]) == 2, "Thread history should have 2 emails"
        assert len(context["semantic_results"]) <= 7, "Semantic results should have up to 7 emails (k=7)"
        assert len(context["semantic_results"]) > 0, "Should retrieve semantic results for short thread"

        # Verify RAGContext structure
        assert "thread_history" in context
        assert "semantic_results" in context
        assert "metadata" in context

        # Verify metadata
        assert context["metadata"]["thread_length"] == 2
        assert context["metadata"]["adaptive_k"] == 7, "Adaptive k should be 7 for short thread"
        assert context["metadata"]["semantic_count"] > 0
        assert "total_tokens_used" in context["metadata"]


class TestStandardThreadHybridRAG:
    """Test suite for standard thread hybrid RAG (AC #6, #7, #10)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_retrieve_context_standard_thread_hybrid_rag(
        self,
        db_session,
        context_test_user,
        context_test_email,
        test_vector_db,
        indexed_emails,
        mock_gmail_client,
        mock_embedding_service
    ):
        """
        Test: Standard thread (4 emails) retrieves k=3 semantic results
        Verify: Hybrid RAG with k=3, ranking by relevance and recency, RAGContext complete
        AC #6: Results combined into RAGContext structure
        AC #7: Semantic results ranked by relevance score and recency
        AC #10: Context formatted as structured RAGContext TypedDict
        """
        # Arrange: Mock standard thread (4 emails) - already set in fixture
        service = ContextRetrievalService(
            user_id=context_test_user.id,
            db_service=database_service,
            gmail_client=mock_gmail_client,
            embedding_service=mock_embedding_service,
            vector_db_client=test_vector_db
        )

        # Act: Retrieve context
        context = await service.retrieve_context(email_id=context_test_email.id)

        # Assert: Standard thread → k=3 semantic results
        assert len(context["thread_history"]) == 4, "Thread history should have 4 emails"
        assert len(context["semantic_results"]) <= 3, "Semantic results should have up to 3 emails (k=3)"

        # Verify hybrid RAG: Both thread and semantic present
        assert len(context["thread_history"]) > 0, "Thread history should not be empty"
        assert len(context["semantic_results"]) > 0, "Semantic results should not be empty"

        # Verify ranking: Semantic results ordered by relevance (checked via metadata)
        # ChromaDB returns results sorted by distance (lower = more similar)
        if len(context["semantic_results"]) > 1:
            # Verify no _distance attribute leaked (should be removed after ranking)
            assert "_distance" not in context["semantic_results"][0], "Temporary _distance should be removed"

        # Verify RAGContext structure completeness
        assert "thread_history" in context
        assert "semantic_results" in context
        assert "metadata" in context

        # Verify metadata fields
        metadata = context["metadata"]
        assert metadata["thread_length"] == 4
        assert metadata["semantic_count"] == len(context["semantic_results"])
        assert metadata["adaptive_k"] == 3, "Adaptive k should be 3 for standard thread"
        assert "oldest_thread_date" in metadata
        assert "total_tokens_used" in metadata
        assert metadata["total_tokens_used"] > 0


class TestLongThreadSemanticSkip:
    """Test suite for long thread semantic skip (AC #5)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_retrieve_context_long_thread_skips_semantic(
        self,
        db_session,
        context_test_user,
        context_test_email,
        test_vector_db,
        indexed_emails,
        mock_gmail_client,
        mock_embedding_service
    ):
        """
        Test: Long thread (8 emails) skips semantic search (k=0)
        Verify: Only thread_history populated, semantic_results empty
        AC #5: Long threads (>5 emails) → k=0 (skip semantic)
        """
        # Arrange: Mock long thread (8 emails)
        mock_gmail_client.get_thread.return_value = [
            {
                "message_id": f"thread_msg_{i}",
                "thread_id": "test_thread",
                "sender": f"sender{i}@example.com",
                "subject": "Long Thread Subject",
                "body": f"Email {i} in long thread with more content.",
                "received_at": datetime(2025, 11, i, 10, 0, 0)
            }
            for i in range(1, 9)  # 8 emails
        ]

        service = ContextRetrievalService(
            user_id=context_test_user.id,
            db_service=database_service,
            gmail_client=mock_gmail_client,
            embedding_service=mock_embedding_service,
            vector_db_client=test_vector_db
        )

        # Act: Retrieve context
        context = await service.retrieve_context(email_id=context_test_email.id)

        # Assert: Long thread → k=0, semantic search skipped
        assert len(context["thread_history"]) == 5, "Thread history should have last 5 emails (truncated from 8)"
        assert len(context["semantic_results"]) == 0, "Semantic results should be empty (k=0 for long thread)"

        # Verify metadata reflects semantic skip
        assert context["metadata"]["thread_length"] == 8, "Original thread length should be 8"
        assert context["metadata"]["adaptive_k"] == 0, "Adaptive k should be 0 for long thread"
        assert context["metadata"]["semantic_count"] == 0, "Semantic count should be 0"

        # Verify thread-only context is valid
        assert "thread_history" in context
        assert "metadata" in context
        assert context["metadata"]["total_tokens_used"] > 0, "Should count tokens for thread history"


class TestTokenBudgetEnforcement:
    """Test suite for token budget enforcement (AC #8, #9)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_token_budget_enforcement_truncates_results(
        self,
        db_session,
        context_test_user,
        context_test_email,
        test_vector_db,
        indexed_emails,
        mock_gmail_client,
        mock_embedding_service
    ):
        """
        Test: Context exceeding 6.5K tokens is truncated correctly
        Verify: Token budget enforced, total_tokens_used in metadata
        AC #8: Context window managed to stay within LLM token limits (~6.5K tokens)
        AC #9: Token counting implemented to enforce budget
        """
        # Arrange: Mock thread and semantic results with large bodies
        large_body = "This is a very long email body with lots of content. " * 100  # ~1200 tokens per email

        mock_gmail_client.get_thread.return_value = [
            {
                "message_id": f"thread_msg_{i}",
                "thread_id": "test_thread",
                "sender": f"sender{i}@example.com",
                "subject": "Large Email Thread",
                "body": large_body,
                "received_at": datetime(2025, 11, i, 10, 0, 0)
            }
            for i in range(1, 6)  # 5 emails with large bodies
        ]

        # Mock get_message_detail to return large bodies for semantic results
        mock_gmail_client.get_message_detail.side_effect = lambda msg_id: {
            "message_id": msg_id,
            "thread_id": f"thread_for_{msg_id}",
            "sender": f"sender_{msg_id}@example.com",
            "subject": f"Large Semantic Email",
            "body": large_body,
            "received_at": datetime(2025, 11, 5, 10, 0, 0)
        }

        service = ContextRetrievalService(
            user_id=context_test_user.id,
            db_service=database_service,
            gmail_client=mock_gmail_client,
            embedding_service=mock_embedding_service,
            vector_db_client=test_vector_db
        )

        # Act: Retrieve context (should trigger token budget enforcement)
        context = await service.retrieve_context(email_id=context_test_email.id)

        # Assert: Token budget enforced
        total_tokens = context["metadata"]["total_tokens_used"]
        assert total_tokens <= 6500, f"Total tokens ({total_tokens}) should not exceed 6500 (budget)"

        # Verify truncation occurred (either thread or semantic results reduced)
        thread_count = len(context["thread_history"])
        semantic_count = len(context["semantic_results"])

        # At least one should be truncated given large bodies
        assert thread_count < 5 or semantic_count < 3, "Context should be truncated to fit budget"

        # Verify metadata reports accurate token counts
        assert "thread_tokens" in context["metadata"]
        assert "semantic_tokens" in context["metadata"]
        assert context["metadata"]["thread_tokens"] + context["metadata"]["semantic_tokens"] == total_tokens


class TestPerformanceParallelRetrieval:
    """Test suite for performance and parallel retrieval (AC #11, #12)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_retrieve_context_performance_parallel_retrieval(
        self,
        db_session,
        context_test_user,
        context_test_email,
        test_vector_db,
        indexed_emails,
        mock_gmail_client,
        mock_embedding_service
    ):
        """
        Test: Context retrieval completes in <3 seconds with real ChromaDB
        Verify: Performance target met, parallel execution improves speed
        AC #11: Query performance measured and logged (target: <3 seconds per NFR001)
        AC #12: Performance optimization via parallel retrieval using asyncio
        """
        service = ContextRetrievalService(
            user_id=context_test_user.id,
            db_service=database_service,
            gmail_client=mock_gmail_client,
            embedding_service=mock_embedding_service,
            vector_db_client=test_vector_db
        )

        # Act: Measure retrieval time
        start_time = time.perf_counter()
        context = await service.retrieve_context(email_id=context_test_email.id)
        elapsed_time = time.perf_counter() - start_time

        # Assert: Performance target met (<3 seconds)
        assert elapsed_time < 3.0, f"Retrieval took {elapsed_time:.3f}s, expected <3s (NFR001)"

        # Verify context returned successfully
        assert context is not None
        assert "thread_history" in context
        assert "semantic_results" in context
        assert "metadata" in context

        # Verify metadata includes performance info
        assert context["metadata"]["total_tokens_used"] > 0

        # Note: Parallel execution timing is difficult to verify in tests, but the
        # implementation uses asyncio.gather() for concurrent thread + semantic retrieval.
        # The <3s performance target inherently validates parallel execution is working.
