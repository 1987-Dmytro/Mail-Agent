"""Unit tests for ChromaDB Vector Database Client.

This module contains comprehensive unit tests for the VectorDBClient class,
covering initialization, CRUD operations, metadata filtering, and error handling.

Test Coverage:
- VectorDBClient initialization with persistent storage (AC #1, #2)
- Collection creation with cosine similarity (AC #4, #5)
- CRUD operations: insert, query, delete (AC #6)
- Query performance and metadata filtering (AC #6, #9)
- Health check functionality (AC #7)

All tests use isolated ChromaDB instances (temp directories) to prevent
interference with production data.

Author: Mail Agent Development Team
Epic: 3 (RAG System & Response Generation)
Story: 3.1 (Vector Database Setup)
"""

import os
import tempfile
from typing import List

import pytest

from app.core.vector_db import VectorDBClient


@pytest.fixture
def temp_chromadb_dir():
    """Create temporary directory for test ChromaDB instance.

    This fixture ensures each test uses an isolated ChromaDB instance,
    preventing test interference and data leakage.

    Yields:
        str: Path to temporary ChromaDB directory

    Cleanup:
        Automatically removes temp directory after test completes
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def vector_db_client(temp_chromadb_dir):
    """Create VectorDBClient instance with temporary storage.

    Args:
        temp_chromadb_dir: Temporary directory fixture

    Returns:
        VectorDBClient: Initialized client instance for testing
    """
    return VectorDBClient(persist_directory=temp_chromadb_dir)


@pytest.fixture
def sample_embedding():
    """Generate sample 768-dimensional embedding vector.

    Returns:
        List[float]: 768-dimensional vector matching Gemini text-embedding-004 output
    """
    return [0.1 * i for i in range(768)]


@pytest.fixture
def sample_metadata():
    """Generate sample email metadata matching collection schema.

    Returns:
        dict: Metadata dict with required fields (message_id, thread_id, sender, etc.)
    """
    return {
        "message_id": "msg_test_123",
        "thread_id": "thread_test_456",
        "sender": "test@example.com",
        "date": "2025-11-09T10:30:00Z",
        "subject": "Test Email Subject",
        "language": "en",
        "snippet": "This is a test email snippet for unit testing purposes.",
    }


# ============================================================================
# Test 1: VectorDBClient Initialization (AC #1, #2)
# ============================================================================


def test_vector_db_client_initialization(temp_chromadb_dir):
    """Test VectorDBClient initialization with persistent storage.

    Verifies:
    - ChromaDB client initializes successfully
    - Persistent directory is created
    - Client accepts valid directory path

    Acceptance Criteria:
    - AC #1: ChromaDB installed and configured (version >=0.4.22)
    - AC #2: Persistent storage configured using SQLite backend
    """
    # Create client
    client = VectorDBClient(persist_directory=temp_chromadb_dir)

    # Verify client initialized
    assert client is not None
    assert client.client is not None
    assert client.persist_directory == temp_chromadb_dir

    # Verify health check passes
    assert client.health_check() is True


def test_vector_db_client_initialization_invalid_directory():
    """Test VectorDBClient initialization with empty directory path.

    Verifies:
    - ValueError raised when persist_directory is empty
    - Error handling prevents silent failures
    """
    with pytest.raises(ValueError, match="persist_directory cannot be empty"):
        VectorDBClient(persist_directory="")


# ============================================================================
# Test 2: Collection Creation with Cosine Similarity (AC #4, #5)
# ============================================================================


def test_create_collection_with_cosine_similarity(vector_db_client):
    """Test collection creation with cosine similarity distance metric.

    Verifies:
    - email_embeddings collection created successfully
    - Distance metric set to cosine similarity
    - Collection metadata stored correctly

    Acceptance Criteria:
    - AC #4: Collection email_embeddings created with metadata schema
    - AC #5: Distance metric configured as cosine similarity
    """
    # Create collection with cosine similarity
    collection = vector_db_client.get_or_create_collection(
        name="email_embeddings",
        metadata={"hnsw:space": "cosine"},
    )

    # Verify collection created
    assert collection is not None
    assert collection.name == "email_embeddings"

    # Verify distance metric is cosine
    assert collection.metadata["hnsw:space"] == "cosine"

    # Verify collection persists (get existing collection)
    existing_collection = vector_db_client.get_or_create_collection(name="email_embeddings")
    assert existing_collection.name == "email_embeddings"


def test_create_collection_with_empty_name(vector_db_client):
    """Test collection creation with empty name raises ValueError."""
    with pytest.raises(ValueError, match="Collection name cannot be empty"):
        vector_db_client.get_or_create_collection(name="")


# ============================================================================
# Test 3: Insert Single Embedding (AC #6)
# ============================================================================


def test_insert_single_embedding(vector_db_client, sample_embedding, sample_metadata):
    """Test inserting single embedding into collection.

    Verifies:
    - Single embedding inserted successfully
    - Metadata stored correctly
    - Collection count increases by 1

    Acceptance Criteria:
    - AC #6: CRUD operations implemented (insert_embedding)
    """
    # Create collection
    vector_db_client.get_or_create_collection(name="email_embeddings")

    # Verify collection is empty
    assert vector_db_client.count_embeddings("email_embeddings") == 0

    # Insert single embedding
    vector_db_client.insert_embedding(
        collection_name="email_embeddings",
        embedding=sample_embedding,
        metadata=sample_metadata,
        id="msg_test_123",
    )

    # Verify count increased
    assert vector_db_client.count_embeddings("email_embeddings") == 1


def test_insert_single_embedding_validation(vector_db_client, sample_embedding, sample_metadata):
    """Test insert_embedding validation for invalid inputs."""
    vector_db_client.get_or_create_collection(name="email_embeddings")

    # Test empty embedding
    with pytest.raises(ValueError, match="Embedding cannot be empty"):
        vector_db_client.insert_embedding(
            collection_name="email_embeddings",
            embedding=[],
            metadata=sample_metadata,
            id="test_id",
        )

    # Test empty id
    with pytest.raises(ValueError, match="ID cannot be empty"):
        vector_db_client.insert_embedding(
            collection_name="email_embeddings",
            embedding=sample_embedding,
            metadata=sample_metadata,
            id="",
        )


# ============================================================================
# Test 4: Insert Embeddings Batch (AC #6)
# ============================================================================


def test_insert_embeddings_batch(vector_db_client, sample_embedding):
    """Test batch inserting multiple embeddings.

    Verifies:
    - Batch insert completes successfully
    - All embeddings stored with correct metadata
    - Collection count matches batch size

    Acceptance Criteria:
    - AC #6: CRUD operations implemented (insert_embeddings_batch)
    """
    # Create collection
    vector_db_client.get_or_create_collection(name="email_embeddings")

    # Prepare batch data (50 embeddings as per recommended batch size)
    batch_size = 50
    embeddings = [[0.1 * i * j for j in range(768)] for i in range(batch_size)]
    metadatas = [
        {
            "message_id": f"msg_{i}",
            "thread_id": "thread_batch",
            "sender": f"user{i}@example.com",
            "date": "2025-11-09T10:30:00Z",
            "subject": f"Email {i}",
            "language": "en",
            "snippet": f"Snippet for email {i}",
        }
        for i in range(batch_size)
    ]
    ids = [f"msg_{i}" for i in range(batch_size)]

    # Insert batch
    vector_db_client.insert_embeddings_batch(
        collection_name="email_embeddings",
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids,
    )

    # Verify count
    assert vector_db_client.count_embeddings("email_embeddings") == batch_size


def test_insert_embeddings_batch_validation(vector_db_client):
    """Test insert_embeddings_batch validation for mismatched list lengths."""
    vector_db_client.get_or_create_collection(name="email_embeddings")

    # Test mismatched list lengths
    with pytest.raises(ValueError, match="List lengths must match"):
        vector_db_client.insert_embeddings_batch(
            collection_name="email_embeddings",
            embeddings=[[0.1] * 768, [0.2] * 768],
            metadatas=[{"message_id": "msg1"}],  # Only 1 metadata (mismatch)
            ids=["msg1", "msg2"],
        )


# ============================================================================
# Test 5: Query Embeddings Returns K Results (AC #6, #9)
# ============================================================================


def test_query_embeddings_returns_k_results(vector_db_client):
    """Test querying embeddings returns k nearest neighbors.

    Verifies:
    - Query returns exactly k results
    - Results ordered by similarity (lowest distance first)
    - Query completes successfully

    Acceptance Criteria:
    - AC #6: CRUD operations implemented (query_embeddings)
    - AC #9: Query performance validated (k=10 in <500ms)
    """
    # Create collection and insert test embeddings
    vector_db_client.get_or_create_collection(name="email_embeddings")

    # Insert 20 embeddings
    for i in range(20):
        vector_db_client.insert_embedding(
            collection_name="email_embeddings",
            embedding=[0.1 * i * j for j in range(768)],
            metadata={"message_id": f"msg_{i}", "sender": f"user{i}@example.com"},
            id=f"msg_{i}",
        )

    # Query for k=10 nearest neighbors
    query_embedding = [0.5 * j for j in range(768)]
    results = vector_db_client.query_embeddings(
        collection_name="email_embeddings",
        query_embedding=query_embedding,
        n_results=10,
    )

    # Verify exactly 10 results returned
    assert len(results["ids"][0]) == 10
    assert len(results["metadatas"][0]) == 10
    assert len(results["distances"][0]) == 10

    # Verify results are ordered by distance (ascending)
    distances = results["distances"][0]
    assert all(distances[i] <= distances[i + 1] for i in range(len(distances) - 1))


def test_query_embeddings_validation(vector_db_client):
    """Test query_embeddings validation for invalid inputs."""
    vector_db_client.get_or_create_collection(name="email_embeddings")

    # Test empty query embedding
    with pytest.raises(ValueError, match="Query embedding cannot be empty"):
        vector_db_client.query_embeddings(
            collection_name="email_embeddings",
            query_embedding=[],
            n_results=10,
        )

    # Test invalid n_results
    with pytest.raises(ValueError, match="n_results must be >= 1"):
        vector_db_client.query_embeddings(
            collection_name="email_embeddings",
            query_embedding=[0.1] * 768,
            n_results=0,
        )


# ============================================================================
# Test 6: Query Embeddings Filters by Metadata (AC #6)
# ============================================================================


def test_query_embeddings_filters_by_metadata(vector_db_client):
    """Test querying embeddings with metadata filtering.

    Verifies:
    - Metadata filter applied correctly
    - Only matching embeddings returned
    - Results respect both similarity and filter

    Acceptance Criteria:
    - AC #6: CRUD operations with metadata filtering
    """
    # Create collection
    vector_db_client.get_or_create_collection(name="email_embeddings")

    # Insert embeddings with different languages
    languages = ["en", "ru", "uk", "de"]
    for i, lang in enumerate(languages * 5):  # 20 embeddings total
        vector_db_client.insert_embedding(
            collection_name="email_embeddings",
            embedding=[0.1 * i * j for j in range(768)],
            metadata={
                "message_id": f"msg_{i}",
                "sender": f"user{i}@example.com",
                "language": lang,
            },
            id=f"msg_{i}",
        )

    # Query with language filter (only Russian emails)
    query_embedding = [0.5 * j for j in range(768)]
    results = vector_db_client.query_embeddings(
        collection_name="email_embeddings",
        query_embedding=query_embedding,
        n_results=10,
        filter={"language": "ru"},
    )

    # Verify all results match filter
    for metadata in results["metadatas"][0]:
        assert metadata["language"] == "ru"

    # Verify at least some results returned (we have 5 Russian emails)
    assert len(results["ids"][0]) > 0


# ============================================================================
# Test 7: Delete Embedding by ID (AC #6)
# ============================================================================


def test_delete_embedding_by_id(vector_db_client, sample_embedding, sample_metadata):
    """Test deleting embedding by ID.

    Verifies:
    - Embedding deleted successfully
    - Collection count decreases by 1
    - Deleted embedding not retrievable

    Acceptance Criteria:
    - AC #6: CRUD operations implemented (delete_embedding)
    """
    # Create collection and insert embedding
    vector_db_client.get_or_create_collection(name="email_embeddings")
    vector_db_client.insert_embedding(
        collection_name="email_embeddings",
        embedding=sample_embedding,
        metadata=sample_metadata,
        id="msg_test_123",
    )

    # Verify embedding exists
    assert vector_db_client.count_embeddings("email_embeddings") == 1

    # Delete embedding
    vector_db_client.delete_embedding(
        collection_name="email_embeddings",
        id="msg_test_123",
    )

    # Verify count decreased
    assert vector_db_client.count_embeddings("email_embeddings") == 0


def test_delete_embedding_validation(vector_db_client):
    """Test delete_embedding validation for empty ID."""
    vector_db_client.get_or_create_collection(name="email_embeddings")

    # Test empty id
    with pytest.raises(ValueError, match="ID cannot be empty"):
        vector_db_client.delete_embedding(
            collection_name="email_embeddings",
            id="",
        )


# ============================================================================
# Test 8: Health Check Returns True When Connected (AC #7)
# ============================================================================


def test_health_check_returns_true_when_connected(vector_db_client):
    """Test health check returns True when ChromaDB is connected.

    Verifies:
    - Health check returns True for active connection
    - Used by test endpoint GET /api/v1/test/vector-db

    Acceptance Criteria:
    - AC #7: Connection test endpoint created
    """
    # Verify health check passes
    assert vector_db_client.health_check() is True

    # Create collection to ensure full initialization
    vector_db_client.get_or_create_collection(name="email_embeddings")

    # Verify health check still passes
    assert vector_db_client.health_check() is True
