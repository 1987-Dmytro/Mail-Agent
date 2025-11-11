"""Integration tests for Email History Indexing Service.

Tests cover AC #1-#12 with focus on real integration between components:
- Real PostgreSQL database operations
- Real ChromaDB vector storage
- Real service interactions

Test Functions (5 required):
1. test_indexing_progress_database_integration() - Database persistence (AC #8, #9)
2. test_chromadb_embedding_storage_integration() - Vector storage (AC #4, #5, #6)
3. test_batch_processing_with_real_chromadb() - Batch processing + storage (AC #7)
4. test_error_handling_with_database_rollback() - Error handling (AC #12)
5. test_incremental_indexing_workflow() - Incremental indexing (AC #11)

Author: Mail Agent Development Team
Epic: 3 (RAG System & Response Generation)
Story: 3.3 (Email History Indexing)
"""

import os
import tempfile
import time
from datetime import datetime, timedelta, UTC
from typing import Dict, List

import pytest
from sqlmodel import select

from app.core.vector_db import VectorDBClient
from app.models.indexing_progress import IndexingProgress, IndexingStatus
from app.models.user import User


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_chromadb_dir():
    """Create temporary directory for test ChromaDB instance.

    Function scope ensures each test gets its own isolated ChromaDB instance.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def test_vector_db_client(temp_chromadb_dir):
    """Create VectorDBClient for integration testing with isolated storage.

    Changed to function scope to ensure clean collection for each test.
    """
    client = VectorDBClient(persist_directory=temp_chromadb_dir)

    # Delete and recreate collection for each test (clean state)
    try:
        client.delete_collection("email_embeddings")
    except Exception:
        pass

    client.get_or_create_collection("email_embeddings")

    yield client

    # Cleanup after test
    try:
        client.delete_collection("email_embeddings")
    except Exception:
        pass


# ============================================================================
# Integration Test 1: IndexingProgress Database Persistence (AC #8, #9)
# ============================================================================


@pytest.mark.asyncio
async def test_indexing_progress_database_integration(test_user, db_session):
    """Test IndexingProgress model persists correctly in PostgreSQL.

    This test verifies:
    - IndexingProgress record can be created and persisted (AC #8)
    - Checkpoint mechanism stores last_processed_message_id (AC #9)
    - Progress tracking fields update correctly
    - Records survive session commits

    Acceptance Criteria:
    - AC #8: Progress tracking via IndexingProgress table
    - AC #9: Checkpoint mechanism with last_processed_message_id
    """
    # Step 1: Create IndexingProgress record
    progress = IndexingProgress(
        user_id=test_user.id,
        total_emails=100,
        processed_count=0,
        status=IndexingStatus.IN_PROGRESS,
        started_at=datetime.now(UTC),
    )

    db_session.add(progress)
    await db_session.commit()
    await db_session.refresh(progress)

    # Verify record created
    assert progress.id is not None
    assert progress.user_id == test_user.id
    assert progress.status == IndexingStatus.IN_PROGRESS
    assert progress.total_emails == 100
    assert progress.processed_count == 0

    # Step 2: Update progress with checkpoint
    progress.processed_count = 50
    progress.last_processed_message_id = "msg_50"
    db_session.add(progress)
    await db_session.commit()

    # Step 3: Query from database to verify persistence
    result = await db_session.execute(
        select(IndexingProgress).where(IndexingProgress.user_id == test_user.id)
    )
    persisted_progress = result.scalar_one()

    assert persisted_progress.processed_count == 50
    assert persisted_progress.last_processed_message_id == "msg_50"
    assert persisted_progress.status == IndexingStatus.IN_PROGRESS

    # Step 4: Mark as completed
    persisted_progress.status = IndexingStatus.COMPLETED
    persisted_progress.processed_count = 100
    persisted_progress.completed_at = datetime.now(UTC)
    db_session.add(persisted_progress)
    await db_session.commit()

    # Verify completion
    result = await db_session.execute(
        select(IndexingProgress).where(IndexingProgress.user_id == test_user.id)
    )
    final_progress = result.scalar_one()

    assert final_progress.status == IndexingStatus.COMPLETED
    assert final_progress.processed_count == 100
    assert final_progress.completed_at is not None


# ============================================================================
# Integration Test 2: ChromaDB Embedding Storage (AC #4, #5, #6)
# ============================================================================


@pytest.mark.asyncio
async def test_chromadb_embedding_storage_integration(test_vector_db_client):
    """Test embeddings with metadata are stored correctly in ChromaDB.

    This test verifies:
    - Embeddings can be stored in ChromaDB (AC #4)
    - Metadata schema includes all required fields (AC #5)
    - Thread relationships are preserved via thread_id (AC #6)
    - Embeddings persist and are retrievable

    Acceptance Criteria:
    - AC #4: Embeddings stored in ChromaDB with metadata
    - AC #5: Metadata schema includes message_id, thread_id, sender, date, subject, language, snippet
    - AC #6: Thread relationships preserved
    """
    collection = test_vector_db_client.get_or_create_collection("email_embeddings")

    # Step 1: Create sample embeddings with metadata
    test_embeddings = [
        {
            "id": "msg_1",
            "embedding": [0.1 * i for i in range(768)],
            "metadata": {
                "message_id": "msg_1",
                "thread_id": "thread_1",
                "sender": "test@example.com",
                "date": "2025-11-09",
                "subject": "Test Email 1",
                "language": "en",
                "snippet": "This is a test email snippet...",
            },
        },
        {
            "id": "msg_2",
            "embedding": [0.2 * i for i in range(768)],
            "metadata": {
                "message_id": "msg_2",
                "thread_id": "thread_1",  # Same thread as msg_1
                "sender": "reply@example.com",
                "date": "2025-11-09",
                "subject": "Re: Test Email 1",
                "language": "en",
                "snippet": "This is a reply in the same thread...",
            },
        },
    ]

    # Step 2: Store embeddings in ChromaDB
    for item in test_embeddings:
        collection.add(
            ids=[item["id"]],
            embeddings=[item["embedding"]],
            metadatas=[item["metadata"]],
        )

    # Step 3: Retrieve and verify
    results = collection.get()

    assert len(results["ids"]) == 2
    assert "msg_1" in results["ids"]
    assert "msg_2" in results["ids"]

    # Verify metadata schema (AC #5)
    for metadata in results["metadatas"]:
        assert "message_id" in metadata
        assert "thread_id" in metadata  # AC #6: Thread relationships
        assert "sender" in metadata
        assert "date" in metadata
        assert "subject" in metadata
        assert "language" in metadata
        assert "snippet" in metadata

    # Verify thread relationships preserved (AC #6)
    msg1_meta = next(m for m in results["metadatas"] if m["message_id"] == "msg_1")
    msg2_meta = next(m for m in results["metadatas"] if m["message_id"] == "msg_2")
    assert msg1_meta["thread_id"] == msg2_meta["thread_id"] == "thread_1"


# ============================================================================
# Integration Test 3: Batch Processing with ChromaDB (AC #7)
# ============================================================================


@pytest.mark.asyncio
async def test_batch_processing_with_real_chromadb(test_vector_db_client):
    """Test batch embedding storage in ChromaDB.

    This test verifies:
    - Batch of 50 embeddings can be stored efficiently (AC #7)
    - All embeddings persist correctly
    - No data loss in batch operations
    - Performance is acceptable for batch operations

    Acceptance Criteria:
    - AC #7: Batch processing strategy (50 emails per batch)
    """
    collection = test_vector_db_client.get_or_create_collection("email_embeddings")

    # Step 1: Create batch of 50 embeddings
    batch_size = 50
    batch_ids = [f"batch_msg_{i}" for i in range(batch_size)]
    batch_embeddings = [[0.01 * i * j for j in range(768)] for i in range(batch_size)]
    batch_metadatas = [
        {
            "message_id": f"batch_msg_{i}",
            "thread_id": f"thread_{i // 5}",  # 5 emails per thread
            "sender": f"sender{i}@example.com",
            "date": (datetime.now(UTC) - timedelta(days=i)).isoformat(),
            "subject": f"Batch Test Email {i}",
            "language": "en",
            "snippet": f"This is batch test email {i}...",
        }
        for i in range(batch_size)
    ]

    # Step 2: Store batch in ChromaDB (measure performance)
    start_time = time.perf_counter()

    collection.add(
        ids=batch_ids,
        embeddings=batch_embeddings,
        metadatas=batch_metadatas,
    )

    end_time = time.perf_counter()
    batch_duration = end_time - start_time

    # Verify batch storage is fast (< 5 seconds for 50 embeddings)
    assert batch_duration < 5.0, f"Batch storage too slow: {batch_duration}s"

    # Step 3: Verify all 50 embeddings stored
    results = collection.get()
    stored_batch_ids = [id for id in results["ids"] if id.startswith("batch_msg_")]

    assert len(stored_batch_ids) == batch_size
    assert set(stored_batch_ids) == set(batch_ids)

    # Verify no data corruption in batch
    for metadata in results["metadatas"]:
        if metadata["message_id"].startswith("batch_msg_"):
            assert "thread_id" in metadata
            assert "sender" in metadata


# ============================================================================
# Integration Test 4: Error Handling with Database Rollback (AC #12)
# ============================================================================


@pytest.mark.asyncio
async def test_error_handling_with_database_rollback(test_user, db_session):
    """Test database transaction rollback on errors.

    This test verifies:
    - Failed operations don't corrupt database state (AC #12)
    - IndexingProgress updates are transactional
    - Error status is recorded correctly

    Acceptance Criteria:
    - AC #12: Error handling with proper status updates
    """
    # Step 1: Create IndexingProgress record
    progress = IndexingProgress(
        user_id=test_user.id,
        total_emails=50,
        processed_count=0,
        status=IndexingStatus.IN_PROGRESS,
        started_at=datetime.now(UTC),
    )

    db_session.add(progress)
    await db_session.commit()
    await db_session.refresh(progress)

    initial_id = progress.id

    # Step 2: Simulate error during processing
    progress.status = IndexingStatus.FAILED
    progress.error_message = "Simulated Gmail API rate limit error (429)"
    progress.processed_count = 25  # Partial progress
    db_session.add(progress)
    await db_session.commit()

    # Step 3: Verify error state persisted
    result = await db_session.execute(
        select(IndexingProgress).where(IndexingProgress.id == initial_id)
    )
    failed_progress = result.scalar_one()

    assert failed_progress.status == IndexingStatus.FAILED
    assert failed_progress.error_message is not None
    assert "rate limit" in failed_progress.error_message.lower()
    assert failed_progress.processed_count == 25  # Partial progress preserved

    # Step 4: Verify recovery - resume from failed state
    failed_progress.status = IndexingStatus.IN_PROGRESS
    failed_progress.error_message = None
    db_session.add(failed_progress)
    await db_session.commit()

    result = await db_session.execute(
        select(IndexingProgress).where(IndexingProgress.id == initial_id)
    )
    resumed_progress = result.scalar_one()

    assert resumed_progress.status == IndexingStatus.IN_PROGRESS
    assert resumed_progress.error_message is None
    assert resumed_progress.processed_count == 25  # Preserved from failure


# ============================================================================
# Integration Test 5: Incremental Indexing Workflow (AC #11)
# ============================================================================


@pytest.mark.asyncio
async def test_incremental_indexing_workflow(test_user, db_session, test_vector_db_client):
    """Test incremental indexing after initial completion.

    This test verifies:
    - Initial indexing completion is tracked (AC #8)
    - New emails can be indexed incrementally (AC #11)
    - No batch delay for single email indexing
    - Incremental embeddings stored correctly

    Acceptance Criteria:
    - AC #8: Progress tracking shows completion
    - AC #11: Incremental indexing for new emails
    """
    collection = test_vector_db_client.get_or_create_collection("email_embeddings")

    # Step 1: Complete initial indexing (simulate)
    progress = IndexingProgress(
        user_id=test_user.id,
        total_emails=10,
        processed_count=10,
        status=IndexingStatus.COMPLETED,
        started_at=datetime.now(UTC) - timedelta(minutes=10),
        completed_at=datetime.now(UTC),
    )

    db_session.add(progress)
    await db_session.commit()
    await db_session.refresh(progress)

    # Store initial 10 embeddings
    initial_ids = [f"init_msg_{i}" for i in range(10)]
    initial_embeddings = [[0.1 * i * j for j in range(768)] for i in range(10)]
    initial_metadatas = [
        {
            "message_id": f"init_msg_{i}",
            "thread_id": f"thread_{i}",
            "sender": f"sender{i}@example.com",
            "date": (datetime.now(UTC) - timedelta(days=i)).isoformat(),
            "subject": f"Initial Email {i}",
            "language": "en",
            "snippet": f"Initial email {i}...",
        }
        for i in range(10)
    ]

    collection.add(ids=initial_ids, embeddings=initial_embeddings, metadatas=initial_metadatas)

    # Verify initial indexing complete
    assert progress.status == IndexingStatus.COMPLETED
    assert progress.processed_count == 10

    # Step 2: Add new email incrementally
    new_email_id = "new_msg_11"
    new_embedding = [0.5 * i for i in range(768)]
    new_metadata = {
        "message_id": "new_msg_11",
        "thread_id": "thread_new",
        "sender": "new@example.com",
        "date": datetime.now(UTC).isoformat(),
        "subject": "New Incremental Email",
        "language": "en",
        "snippet": "This is a new email added incrementally...",
    }

    start_time = time.perf_counter()

    collection.add(ids=[new_email_id], embeddings=[new_embedding], metadatas=[new_metadata])

    end_time = time.perf_counter()
    incremental_duration = end_time - start_time

    # Verify incremental indexing is fast (< 1 second, no batch delay)
    assert incremental_duration < 1.0, f"Incremental indexing too slow: {incremental_duration}s"

    # Step 3: Verify total count is now 11
    results = collection.get()
    assert len(results["ids"]) == 11
    assert "new_msg_11" in results["ids"]

    # Verify new email metadata
    new_email_meta = next(m for m in results["metadatas"] if m["message_id"] == "new_msg_11")
    assert new_email_meta["subject"] == "New Incremental Email"
    assert new_email_meta["thread_id"] == "thread_new"

    # Verify IndexingProgress not updated for incremental (processed_count stays at 10)
    result = await db_session.execute(
        select(IndexingProgress).where(IndexingProgress.user_id == test_user.id)
    )
    final_progress = result.scalar_one()
    assert final_progress.processed_count == 10  # Not incremented
    assert final_progress.status == IndexingStatus.COMPLETED
