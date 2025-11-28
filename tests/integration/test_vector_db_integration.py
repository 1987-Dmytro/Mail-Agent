"""Integration tests for ChromaDB Vector Database.

This module contains end-to-end integration tests for the VectorDBClient,
focusing on persistence, semantic search, performance, and API endpoint testing.

Test Coverage:
- Persistence across client restarts (AC #2)
- Semantic search with similar/dissimilar embeddings (AC #6, #9)
- Query performance validation k=10 in <500ms (AC #9)
- Connection test endpoint GET /api/v1/test/vector-db (AC #7)

All tests use isolated test ChromaDB instances to prevent interference
with production data.

Author: Mail Agent Development Team
Epic: 3 (RAG System & Response Generation)
Story: 3.1 (Vector Database Setup)
"""

import tempfile
import time

import pytest
from fastapi.testclient import TestClient

from app.core.vector_db import VectorDBClient


@pytest.fixture
def temp_chromadb_dir():
    """Create temporary directory for test ChromaDB instance.

    Yields:
        str: Path to temporary ChromaDB directory

    Cleanup:
        Automatically removes temp directory after test completes
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# ============================================================================
# Integration Test 1: Vector DB Persistence Survives Restart (AC #2)
# ============================================================================


def test_vector_db_persistence_survives_restart(temp_chromadb_dir):
    """Test that embeddings persist after ChromaDB client restart.

    This test verifies that data is written to persistent SQLite storage
    and survives service restarts (not just in-memory storage).

    Test Steps:
    1. Create ChromaDB client with persistent storage
    2. Insert test embeddings with metadata
    3. Shutdown client (delete instance)
    4. Create new client instance pointing to same directory
    5. Verify all embeddings still exist with correct metadata

    Acceptance Criteria:
    - AC #2: Persistent storage configured using SQLite backend
              (embeddings survive service restarts)
    """
    # Step 1: Create client and collection
    client1 = VectorDBClient(persist_directory=temp_chromadb_dir)
    client1.get_or_create_collection(name="email_embeddings")

    # Step 2: Insert test embeddings
    test_embeddings = [
        {
            "id": "msg_persist_1",
            "embedding": [0.1 * i for i in range(768)],
            "metadata": {
                "message_id": "msg_persist_1",
                "sender": "user1@example.com",
                "subject": "Test Email 1",
            },
        },
        {
            "id": "msg_persist_2",
            "embedding": [0.2 * i for i in range(768)],
            "metadata": {
                "message_id": "msg_persist_2",
                "sender": "user2@example.com",
                "subject": "Test Email 2",
            },
        },
        {
            "id": "msg_persist_3",
            "embedding": [0.3 * i for i in range(768)],
            "metadata": {
                "message_id": "msg_persist_3",
                "sender": "user3@example.com",
                "subject": "Test Email 3",
            },
        },
    ]

    for item in test_embeddings:
        client1.insert_embedding(
            collection_name="email_embeddings",
            embedding=item["embedding"],
            metadata=item["metadata"],
            id=item["id"],
        )

    # Verify count before restart
    assert client1.count_embeddings("email_embeddings") == 3

    # Step 3: Shutdown client (simulate service restart)
    del client1

    # Step 4: Create new client instance pointing to same storage
    client2 = VectorDBClient(persist_directory=temp_chromadb_dir)

    # Step 5: Verify embeddings still exist
    count = client2.count_embeddings("email_embeddings")
    assert count == 3, f"Expected 3 embeddings after restart, got {count}"

    # Query and verify metadata persisted correctly
    query_embedding = [0.15 * i for i in range(768)]
    results = client2.query_embeddings(
        collection_name="email_embeddings",
        query_embedding=query_embedding,
        n_results=3,
    )

    # Verify all 3 embeddings retrieved
    assert len(results["ids"][0]) == 3

    # Verify metadata matches original
    retrieved_ids = set(results["ids"][0])
    expected_ids = {"msg_persist_1", "msg_persist_2", "msg_persist_3"}
    assert retrieved_ids == expected_ids


# ============================================================================
# Integration Test 2: Semantic Search Returns Similar Embeddings (AC #6, #9)
# ============================================================================


def test_semantic_search_returns_similar_embeddings(temp_chromadb_dir):
    """Test semantic search returns embeddings ranked by similarity.

    This test verifies that cosine similarity correctly ranks embeddings,
    with more similar embeddings appearing first in results.

    Test Steps:
    1. Insert 3 embeddings: 2 similar, 1 dissimilar
    2. Query with embedding similar to the "similar" group
    3. Verify results are ranked correctly (similar embeddings first)
    4. Verify distances reflect similarity (lower distance = more similar)

    Acceptance Criteria:
    - AC #6: CRUD operations implemented (query_embeddings with semantic search)
    - AC #9: Query returns correct results ranked by cosine similarity
    """
    # Create client and collection
    client = VectorDBClient(persist_directory=temp_chromadb_dir)
    client.get_or_create_collection(
        name="email_embeddings",
        metadata={"hnsw:space": "cosine"},  # Cosine similarity
    )

    # Insert embeddings with distinct patterns
    # Similar embeddings: alternating small/large values starting with 1.0
    # Dissimilar embedding: all negative values (opposite direction)
    embeddings = [
        {
            "id": "similar_1",
            # Pattern: [1.0, 0.1, 1.0, 0.1, ...]
            "embedding": [1.0 if i % 2 == 0 else 0.1 for i in range(768)],
            "metadata": {"message_id": "similar_1", "group": "A"},
        },
        {
            "id": "similar_2",
            # Pattern: [0.9, 0.15, 0.9, 0.15, ...] (very similar to similar_1)
            "embedding": [0.9 if i % 2 == 0 else 0.15 for i in range(768)],
            "metadata": {"message_id": "similar_2", "group": "A"},
        },
        {
            "id": "dissimilar",
            # Pattern: all negative (opposite direction in vector space)
            "embedding": [-0.5 for _ in range(768)],
            "metadata": {"message_id": "dissimilar", "group": "B"},
        },
    ]

    for item in embeddings:
        client.insert_embedding(
            collection_name="email_embeddings",
            embedding=item["embedding"],
            metadata=item["metadata"],
            id=item["id"],
        )

    # Query with embedding very similar to similar_1 and similar_2
    # Pattern: [0.95, 0.12, 0.95, 0.12, ...] (close to both similar embeddings)
    query_embedding = [0.95 if i % 2 == 0 else 0.12 for i in range(768)]
    results = client.query_embeddings(
        collection_name="email_embeddings",
        query_embedding=query_embedding,
        n_results=3,
    )

    # Verify results are ranked by similarity
    # The top 2 results should be "similar_1" and "similar_2"
    top_2_ids = results["ids"][0][:2]
    assert "similar_1" in top_2_ids, f"Expected 'similar_1' in top 2, got {top_2_ids}"
    assert "similar_2" in top_2_ids, f"Expected 'similar_2' in top 2, got {top_2_ids}"

    # Verify dissimilar embedding has highest distance (appears last)
    assert results["ids"][0][2] == "dissimilar", "Expected dissimilar embedding to rank last"

    # Verify distances are ordered (ascending)
    distances = results["distances"][0]
    assert distances[0] < distances[2], "Most similar should have lowest distance"
    assert distances[1] < distances[2], "Second most similar should have lower distance than dissimilar"


# ============================================================================
# Integration Test 3: Query Performance k=10 Under 500ms (AC #9)
# ============================================================================


def test_query_performance_k10_under_500ms(temp_chromadb_dir):
    """Test that k=10 query completes in under 500ms.

    This test validates the performance target specified in AC #9.
    Query latency must be <500ms to contribute to NFR001 (RAG retrieval <3s).

    Test Steps:
    1. Insert 1000 test embeddings (realistic dataset size)
    2. Perform k=10 query
    3. Measure query time using time.perf_counter()
    4. Verify query completes in <500ms

    Acceptance Criteria:
    - AC #9: Query performance validated: k=10 nearest neighbors completes
             in <500ms (contributes to NFR001)
    """
    # Create client and collection
    client = VectorDBClient(persist_directory=temp_chromadb_dir)
    client.get_or_create_collection(name="email_embeddings")

    # Insert 1000 embeddings (realistic dataset for MVP scale)
    print("Inserting 1000 test embeddings...")
    batch_size = 50
    for batch_start in range(0, 1000, batch_size):
        embeddings = [[0.001 * i * j for j in range(768)] for i in range(batch_start, batch_start + batch_size)]
        metadatas = [
            {
                "message_id": f"msg_{i}",
                "sender": f"user{i}@example.com",
            }
            for i in range(batch_start, batch_start + batch_size)
        ]
        ids = [f"msg_{i}" for i in range(batch_start, batch_start + batch_size)]

        client.insert_embeddings_batch(
            collection_name="email_embeddings",
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )

    # Verify all embeddings inserted
    assert client.count_embeddings("email_embeddings") == 1000

    # Perform k=10 query and measure time
    query_embedding = [0.5 * i for i in range(768)]

    # Warm-up query (exclude from timing to account for lazy loading)
    client.query_embeddings(
        collection_name="email_embeddings",
        query_embedding=query_embedding,
        n_results=10,
    )

    # Timed query
    start_time = time.perf_counter()
    results = client.query_embeddings(
        collection_name="email_embeddings",
        query_embedding=query_embedding,
        n_results=10,
    )
    end_time = time.perf_counter()

    query_time_ms = (end_time - start_time) * 1000

    # Verify results
    assert len(results["ids"][0]) == 10, "Expected exactly 10 results"

    # Verify performance: k=10 query in <500ms
    print(f"Query time: {query_time_ms:.2f}ms")
    assert (
        query_time_ms < 500
    ), f"Query took {query_time_ms:.2f}ms, expected <500ms (AC #9 performance target)"


# ============================================================================
# Integration Test 4: Connection Test Endpoint (AC #7)
# ============================================================================


def test_connection_test_endpoint(temp_chromadb_dir):
    """Test GET /api/v1/test/vector-db endpoint returns connection status.

    This test verifies the connection test endpoint works correctly and
    returns accurate information about the ChromaDB connection.

    Test Steps:
    1. Start FastAPI test client
    2. Override global vector_db_client with test instance
    3. Call GET /api/v1/test/vector-db
    4. Verify 200 status code
    5. Verify response contains connection info

    Acceptance Criteria:
    - AC #7: Connection test endpoint created (GET /api/v1/test/vector-db)
             returning connection status
    """
    # Import FastAPI app and override vector_db_client
    from app.main import app, vector_db_client
    from app.core.config import settings

    # Create test client
    client = TestClient(app)

    # Initialize test vector DB client and override global instance
    test_vector_client = VectorDBClient(persist_directory=temp_chromadb_dir)
    test_vector_client.get_or_create_collection(name="email_embeddings")

    # Insert test embeddings
    for i in range(5):
        test_vector_client.insert_embedding(
            collection_name="email_embeddings",
            embedding=[0.1 * i * j for j in range(768)],
            metadata={"message_id": f"msg_{i}"},
            id=f"msg_{i}",
        )

    # Override global vector_db_client
    import app.main
    app.main.vector_db_client = test_vector_client

    try:
        # Call test endpoint
        response = client.get("/api/v1/test/vector-db")

        # Verify status code
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        # Verify response structure
        data = response.json()
        assert "status" in data, "Response missing 'status' field"
        assert "collection_name" in data, "Response missing 'collection_name' field"
        assert "total_embeddings" in data, "Response missing 'total_embeddings' field"
        assert "distance_metric" in data, "Response missing 'distance_metric' field"
        assert "persist_directory" in data, "Response missing 'persist_directory' field"

        # Verify values
        assert data["status"] == "connected", f"Expected status='connected', got {data['status']}"
        assert data["collection_name"] == "email_embeddings"
        assert data["total_embeddings"] == 5, f"Expected 5 embeddings, got {data['total_embeddings']}"
        assert data["distance_metric"] == "cosine"

    finally:
        # Restore original vector_db_client
        app.main.vector_db_client = None
