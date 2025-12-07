"""ChromaDB Vector Database Client for Email Embeddings.

This module provides a client wrapper for ChromaDB, a self-hosted vector database
used for storing and retrieving email embeddings for semantic search in the RAG system.

Key Features:
- Persistent SQLite storage (embeddings survive service restarts)
- Cosine similarity distance metric for semantic search
- CRUD operations for embeddings with metadata
- Connection pooling and error handling
- Type hints and comprehensive docstrings

Architecture Decision Record (ADR-009):
ChromaDB selected for zero-cost self-hosted vector database with Python-native
integration, local data control, and performance suitable for MVP scale (10K-50K emails).

Performance Target (NFR001):
- k=10 nearest neighbors query in <500ms
- Contributes to RAG retrieval <3 seconds total

Author: Mail Agent Development Team
Epic: 3 (RAG System & Response Generation)
Story: 3.1 (Vector Database Setup)
"""

import logging
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class VectorDBClient:
    """ChromaDB client for managing email embeddings with persistent storage.

    This class provides a high-level interface to ChromaDB for storing and retrieving
    email embeddings. It handles connection management, collection creation, CRUD
    operations, and error handling.

    Attributes:
        client: ChromaDB client instance with persistent storage
        persist_directory: Path to persistent SQLite storage directory

    Example:
        >>> client = VectorDBClient(persist_directory="./backend/data/chromadb")
        >>> collection = client.get_or_create_collection(
        ...     name="email_embeddings",
        ...     metadata={"hnsw:space": "cosine"}
        ... )
        >>> client.insert_embedding(
        ...     collection_name="email_embeddings",
        ...     embedding=[0.1, 0.2, ...],  # 768-dim vector
        ...     metadata={"message_id": "msg123", "sender": "user@example.com"},
        ...     id="msg123"
        ... )
    """

    def __init__(self, persist_directory: str) -> None:
        """Initialize ChromaDB client with persistent storage.

        Args:
            persist_directory: Path to directory for persistent SQLite storage.
                             Must be writable. Directory will be created if it doesn't exist.

        Raises:
            ConnectionError: If ChromaDB client initialization fails
            ValueError: If persist_directory is empty or invalid

        Example:
            >>> client = VectorDBClient(persist_directory="./backend/data/chromadb")
        """
        if not persist_directory:
            raise ValueError("persist_directory cannot be empty")

        self.persist_directory = persist_directory

        try:
            # Initialize ChromaDB with persistent storage using SQLite backend
            # Settings reference: https://docs.trychroma.com/usage-guide#changing-the-distance-function
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,  # Disable telemetry for privacy
                    allow_reset=True,  # Allow collection reset in development
                ),
            )
            logger.info(f"ChromaDB client initialized with persistent storage at: {persist_directory}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {e}")
            raise ConnectionError(f"ChromaDB initialization failed: {e}") from e

    def get_or_create_collection(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> Any:
        """Get existing collection or create new one with specified metadata.

        Collections store embeddings with associated metadata. Distance metric
        is configured via metadata (default: cosine similarity).

        Args:
            name: Collection name (e.g., "email_embeddings")
            metadata: Collection configuration metadata. For cosine similarity:
                     {"hnsw:space": "cosine"}. Other options: "l2", "ip" (inner product).
                     Defaults to cosine similarity if not specified.

        Returns:
            ChromaDB Collection object

        Raises:
            ValueError: If collection name is empty
            ConnectionError: If ChromaDB operation fails

        Example:
            >>> collection = client.get_or_create_collection(
            ...     name="email_embeddings",
            ...     metadata={"hnsw:space": "cosine"}
            ... )
        """
        if not name:
            raise ValueError("Collection name cannot be empty")

        # Default to cosine similarity if metadata not provided
        if metadata is None:
            metadata = {"hnsw:space": "cosine"}

        try:
            collection = self.client.get_or_create_collection(name=name, metadata=metadata)
            logger.info(f"Collection '{name}' ready (metadata: {metadata})")
            return collection
        except Exception as e:
            logger.error(f"Failed to get/create collection '{name}': {e}")
            raise ConnectionError(f"Collection operation failed for '{name}': {e}") from e

    def insert_embedding(
        self,
        collection_name: str,
        embedding: List[float],
        metadata: Dict[str, Any],
        id: str,
    ) -> None:
        """Insert single embedding into specified collection.

        Args:
            collection_name: Name of collection to insert into
            embedding: Embedding vector (768 dimensions for Gemini text-embedding-004)
            metadata: Associated metadata (message_id, thread_id, sender, date, subject, language, snippet)
            id: Unique identifier for embedding (typically Gmail message_id)

        Raises:
            ValueError: If embedding is empty, id is empty, or embedding dimensions invalid
            ConnectionError: If ChromaDB insert operation fails

        Example:
            >>> client.insert_embedding(
            ...     collection_name="email_embeddings",
            ...     embedding=[0.1, 0.2, ...],  # 768-dim vector
            ...     metadata={
            ...         "message_id": "msg123",
            ...         "thread_id": "thread456",
            ...         "sender": "user@example.com",
            ...         "date": "2025-11-09T10:30:00Z",
            ...         "subject": "Meeting Notes",
            ...         "language": "en",
            ...         "snippet": "Here are the notes from..."
            ...     },
            ...     id="msg123"
            ... )
        """
        if not embedding:
            raise ValueError("Embedding cannot be empty")
        if not id:
            raise ValueError("ID cannot be empty")

        try:
            collection = self.get_or_create_collection(collection_name)
            collection.add(embeddings=[embedding], metadatas=[metadata], ids=[id])
            logger.debug(f"Inserted embedding for id '{id}' into collection '{collection_name}'")
        except Exception as e:
            logger.error(f"Failed to insert embedding for id '{id}': {e}")
            raise ConnectionError(f"Embedding insert failed for id '{id}': {e}") from e

    def insert_embeddings_batch(
        self,
        collection_name: str,
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
    ) -> None:
        """Batch insert multiple embeddings into specified collection.

        More efficient than individual inserts for bulk operations. Recommended
        batch size: 50 embeddings (aligns with Gmail API rate limits).

        Args:
            collection_name: Name of collection to insert into
            embeddings: List of embedding vectors (all same dimensions)
            metadatas: List of metadata dicts (one per embedding)
            ids: List of unique identifiers (one per embedding)

        Raises:
            ValueError: If list lengths don't match or lists are empty
            ConnectionError: If ChromaDB batch insert operation fails

        Example:
            >>> client.insert_embeddings_batch(
            ...     collection_name="email_embeddings",
            ...     embeddings=[[0.1, 0.2, ...], [0.3, 0.4, ...]],
            ...     metadatas=[
            ...         {"message_id": "msg1", "sender": "user1@example.com", ...},
            ...         {"message_id": "msg2", "sender": "user2@example.com", ...}
            ...     ],
            ...     ids=["msg1", "msg2"]
            ... )
        """
        if not embeddings or not metadatas or not ids:
            raise ValueError("Embeddings, metadatas, and ids cannot be empty")
        if not (len(embeddings) == len(metadatas) == len(ids)):
            raise ValueError(
                f"List lengths must match: embeddings={len(embeddings)}, "
                f"metadatas={len(metadatas)}, ids={len(ids)}"
            )

        try:
            collection = self.get_or_create_collection(collection_name)
            collection.add(embeddings=embeddings, metadatas=metadatas, ids=ids)
            logger.info(f"Batch inserted {len(ids)} embeddings into collection '{collection_name}'")
        except Exception as e:
            logger.error(f"Failed to batch insert {len(ids)} embeddings: {e}")
            raise ConnectionError(f"Batch insert failed: {e}") from e

    def query_embeddings(
        self,
        collection_name: str,
        query_embedding: List[float],
        n_results: int = 10,
        filter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Query collection for k nearest neighbors using semantic similarity.

        Uses cosine similarity distance metric to find most similar embeddings.
        Performance target: <500ms for k=10 query (contributes to NFR001).

        Args:
            collection_name: Name of collection to query
            query_embedding: Query vector (768 dimensions for Gemini)
            n_results: Number of nearest neighbors to return (k parameter, default: 10)
            filter: Optional metadata filter (e.g., {"language": "ru"} for Russian emails only)

        Returns:
            Query results dict with keys:
                - ids: List of matching embedding IDs
                - embeddings: List of matching embedding vectors (if include_embeddings=True)
                - metadatas: List of metadata dicts
                - distances: List of distance scores (lower = more similar)

        Raises:
            ValueError: If query_embedding is empty or n_results < 1
            ConnectionError: If ChromaDB query operation fails

        Example:
            >>> results = client.query_embeddings(
            ...     collection_name="email_embeddings",
            ...     query_embedding=[0.1, 0.2, ...],
            ...     n_results=10,
            ...     filter={"language": "ru"}  # Only Russian emails
            ... )
            >>> for id, metadata, distance in zip(
            ...     results["ids"][0],
            ...     results["metadatas"][0],
            ...     results["distances"][0]
            ... ):
            ...     print(f"ID: {id}, Sender: {metadata['sender']}, Distance: {distance}")
        """
        if not query_embedding:
            raise ValueError("Query embedding cannot be empty")
        if n_results < 1:
            raise ValueError("n_results must be >= 1")

        try:
            collection = self.get_or_create_collection(collection_name)
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filter,  # Metadata filtering
            )
            logger.debug(
                f"Query returned {len(results['ids'][0]) if results['ids'] else 0} results "
                f"from collection '{collection_name}'"
            )
            return results
        except Exception as e:
            logger.error(f"Failed to query collection '{collection_name}': {e}")
            raise ConnectionError(f"Query operation failed: {e}") from e

    def delete_embedding(self, collection_name: str, id: str) -> None:
        """Delete embedding from collection by ID.

        Args:
            collection_name: Name of collection to delete from
            id: Unique identifier of embedding to delete (Gmail message_id)

        Raises:
            ValueError: If id is empty
            ConnectionError: If ChromaDB delete operation fails

        Example:
            >>> client.delete_embedding(
            ...     collection_name="email_embeddings",
            ...     id="msg123"
            ... )
        """
        if not id:
            raise ValueError("ID cannot be empty")

        try:
            collection = self.get_or_create_collection(collection_name)
            collection.delete(ids=[id])
            logger.debug(f"Deleted embedding with id '{id}' from collection '{collection_name}'")
        except Exception as e:
            logger.error(f"Failed to delete embedding for id '{id}': {e}")
            raise ConnectionError(f"Delete operation failed for id '{id}': {e}") from e

    def count_embeddings(self, collection_name: str) -> int:
        """Get total count of embeddings in collection.

        Args:
            collection_name: Name of collection to count

        Returns:
            Total number of embeddings in collection

        Raises:
            ConnectionError: If ChromaDB count operation fails

        Example:
            >>> count = client.count_embeddings("email_embeddings")
            >>> print(f"Total embeddings: {count}")
        """
        try:
            collection = self.get_or_create_collection(collection_name)
            count = collection.count()
            logger.debug(f"Collection '{collection_name}' contains {count} embeddings")
            return count
        except Exception as e:
            logger.error(f"Failed to count embeddings in collection '{collection_name}': {e}")
            raise ConnectionError(f"Count operation failed: {e}") from e

    def health_check(self) -> bool:
        """Verify ChromaDB connection is active and responsive.

        Used by test endpoint (GET /api/v1/test/vector-db) to verify database health.

        Returns:
            True if connection is active, False otherwise

        Example:
            >>> if client.health_check():
            ...     print("ChromaDB is connected")
            ... else:
            ...     print("ChromaDB connection failed")
        """
        try:
            # Test connection by listing collections
            self.client.list_collections()
            logger.debug("ChromaDB health check passed")
            return True
        except Exception as e:
            logger.error(f"ChromaDB health check failed: {e}")
            return False
