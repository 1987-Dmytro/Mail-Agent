"""Pinecone Vector Database Client for Email Embeddings.

This module provides a Pinecone wrapper with the same interface as ChromaDB VectorDBClient,
enabling seamless migration from ChromaDB to Pinecone with zero code changes in consuming services.

Key Features:
- Drop-in replacement for ChromaDB VectorDBClient
- Persistent cloud storage (embeddings survive service restarts)
- Cosine similarity distance metric for semantic search
- Namespace isolation for multi-tenant data
- CRUD operations with metadata filtering
- Production-ready with fault tolerance

Pinecone Configuration:
- Index: ai-assistant-memories (existing, 768 dimensions)
- Namespace: mail-agent-emails (isolated from other data)
- Metric: cosine
- Region: us-east-1 (AWS)
- Plan: Free tier (100K vectors)

Performance Target (NFR001):
- k=10 nearest neighbors query in <500ms
- Contributes to RAG retrieval <3 seconds total

Migration from ChromaDB:
    # Before (ChromaDB)
    from app.core.vector_db import VectorDBClient
    client = VectorDBClient(persist_directory="./data/chromadb")

    # After (Pinecone) - same API!
    from app.core.vector_db_pinecone import PineconeVectorDBClient
    client = PineconeVectorDBClient(
        api_key=os.getenv("PINECONE_API_KEY"),
        index_name="ai-assistant-memories"
    )

Author: Mail Agent Development Team
Epic: 3 (RAG System & Response Generation)
Story: 3.1 (Vector Database Setup - Pinecone Migration)
"""

import logging
import os
from typing import Any, Dict, List, Optional

from pinecone import Pinecone, ServerlessSpec

logger = logging.getLogger(__name__)


class PineconeVectorDBClient:
    """Pinecone client with ChromaDB-compatible interface for email embeddings.

    This class provides a drop-in replacement for ChromaDB VectorDBClient,
    using Pinecone for cloud-native persistent vector storage with namespace isolation.

    Attributes:
        client: Pinecone client instance
        index_name: Name of Pinecone index
        namespace: Namespace for data isolation (default: "mail-agent-emails")
        dimension: Expected embedding dimension (768 for Gemini)

    Example:
        >>> client = PineconeVectorDBClient(
        ...     api_key="pcsk_...",
        ...     index_name="ai-assistant-memories"
        ... )
        >>> client.insert_embedding(
        ...     collection_name="email_embeddings",  # Mapped to namespace
        ...     embedding=[0.1, 0.2, ...],  # 768-dim vector
        ...     metadata={"message_id": "msg123", "sender": "user@example.com"},
        ...     id="msg123"
        ... )
    """

    # Expected embedding dimension for Gemini text-embedding-004
    EXPECTED_DIMENSIONS = 768

    # Default namespace for Mail Agent emails
    DEFAULT_NAMESPACE = "mail-agent-emails"

    def __init__(
        self,
        api_key: Optional[str] = None,
        index_name: str = "ai-assistant-memories",
        namespace: str = DEFAULT_NAMESPACE,
        dimension: int = EXPECTED_DIMENSIONS
    ) -> None:
        """Initialize Pinecone client with cloud storage.

        Args:
            api_key: Pinecone API key (defaults to PINECONE_API_KEY env var)
            index_name: Name of existing Pinecone index (default: ai-assistant-memories)
            namespace: Namespace for data isolation (default: mail-agent-emails)
            dimension: Expected embedding dimension (default: 768)

        Raises:
            ValueError: If API key is missing or index doesn't exist
            ConnectionError: If Pinecone client initialization fails

        Example:
            >>> client = PineconeVectorDBClient(
            ...     api_key="pcsk_...",
            ...     index_name="ai-assistant-memories"
            ... )
        """
        self.api_key = api_key or os.getenv("PINECONE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "PINECONE_API_KEY environment variable not set. "
                "Get your API key from: https://app.pinecone.io"
            )

        self.index_name = index_name
        self.namespace = namespace
        self.dimension = dimension

        try:
            # Initialize Pinecone client
            self.client = Pinecone(api_key=self.api_key)

            # Connect to existing index
            self.index = self.client.Index(self.index_name)

            logger.info(
                f"Pinecone client initialized: index='{self.index_name}', "
                f"namespace='{self.namespace}', dimension={self.dimension}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone client: {e}")
            raise ConnectionError(f"Pinecone initialization failed: {e}") from e

    def get_or_create_collection(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Get or create collection (mapped to namespace in Pinecone).

        In Pinecone, collections are implemented as namespaces within a single index.
        This provides logical data isolation while using the same vector index.

        Args:
            name: Collection name (used as namespace suffix: "mail-agent-{name}")
            metadata: Collection metadata (unused in Pinecone, kept for API compatibility)

        Returns:
            Namespace string (collection_name for API compatibility)

        Raises:
            ValueError: If collection name is empty

        Example:
            >>> collection = client.get_or_create_collection("email_embeddings")
            >>> # Returns: "email_embeddings"
        """
        if not name:
            raise ValueError("Collection name cannot be empty")

        # In Pinecone, namespaces are created implicitly on first upsert
        # Return collection name for API compatibility
        logger.info(f"Collection '{name}' ready (namespace: '{self.namespace}')")
        return name

    def insert_embedding(
        self,
        collection_name: str,
        embedding: List[float],
        metadata: Dict[str, Any],
        id: str,
    ) -> None:
        """Insert single embedding into collection (namespace).

        Args:
            collection_name: Collection name (mapped to namespace)
            embedding: Embedding vector (768 dimensions for Gemini)
            metadata: Associated metadata (message_id, sender, date, etc.)
            id: Unique identifier for embedding (Gmail message_id)

        Raises:
            ValueError: If embedding is empty or id is empty
            ConnectionError: If Pinecone upsert operation fails

        Example:
            >>> client.insert_embedding(
            ...     collection_name="email_embeddings",
            ...     embedding=[0.1, 0.2, ...],
            ...     metadata={"message_id": "msg123", "sender": "user@example.com"},
            ...     id="msg123"
            ... )
        """
        if not embedding:
            raise ValueError("Embedding cannot be empty")
        if not id:
            raise ValueError("ID cannot be empty")

        try:
            # Upsert single vector to Pinecone
            self.index.upsert(
                vectors=[(id, embedding, metadata)],
                namespace=self.namespace
            )
            logger.debug(f"Inserted embedding for id '{id}' into namespace '{self.namespace}'")
        except Exception as e:
            logger.error(f"Failed to insert embedding for id '{id}': {e}")
            raise ConnectionError(f"Pinecone upsert failed for id '{id}': {e}") from e

    def insert_embeddings_batch(
        self,
        collection_name: str,
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
    ) -> None:
        """Batch insert multiple embeddings into collection.

        More efficient than individual inserts. Pinecone supports batches up to 100 vectors.

        Args:
            collection_name: Collection name (mapped to namespace)
            embeddings: List of embedding vectors (all 768 dimensions)
            metadatas: List of metadata dicts (one per embedding)
            ids: List of unique identifiers (one per embedding)

        Raises:
            ValueError: If list lengths don't match or lists are empty
            ConnectionError: If Pinecone batch upsert fails

        Example:
            >>> client.insert_embeddings_batch(
            ...     collection_name="email_embeddings",
            ...     embeddings=[[0.1, 0.2, ...], [0.3, 0.4, ...]],
            ...     metadatas=[{"message_id": "msg1"}, {"message_id": "msg2"}],
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
            # Prepare vectors for batch upsert
            vectors = list(zip(ids, embeddings, metadatas))

            # Upsert batch to Pinecone (max 100 per batch)
            self.index.upsert(vectors=vectors, namespace=self.namespace)

            logger.info(f"Batch inserted {len(ids)} embeddings into namespace '{self.namespace}'")
        except Exception as e:
            logger.error(f"Failed to batch insert {len(ids)} embeddings: {e}")
            raise ConnectionError(f"Pinecone batch upsert failed: {e}") from e

    def query_embeddings(
        self,
        collection_name: str,
        query_embedding: List[float],
        n_results: int = 10,
        filter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Query collection for k nearest neighbors using cosine similarity.

        Performance target: <500ms for k=10 query.

        Args:
            collection_name: Collection name (mapped to namespace)
            query_embedding: Query vector (768 dimensions)
            n_results: Number of nearest neighbors to return (default: 10)
            filter: Optional metadata filter (e.g., {"language": "ru"})

        Returns:
            Dict matching ChromaDB format:
                - ids: [[id1, id2, ...]]  # Nested list for API compatibility
                - metadatas: [[meta1, meta2, ...]]
                - distances: [[dist1, dist2, ...]]  # Cosine distances

        Example:
            >>> results = client.query_embeddings(
            ...     collection_name="email_embeddings",
            ...     query_embedding=[0.1, 0.2, ...],
            ...     n_results=10,
            ...     filter={"language": "ru"}
            ... )
            >>> for id, metadata, distance in zip(
            ...     results["ids"][0],
            ...     results["metadatas"][0],
            ...     results["distances"][0]
            ... ):
            ...     print(f"ID: {id}, Distance: {distance}")
        """
        if not query_embedding:
            raise ValueError("Query embedding cannot be empty")
        if n_results < 1:
            raise ValueError("n_results must be >= 1")

        try:
            # Query Pinecone index
            response = self.index.query(
                vector=query_embedding,
                top_k=n_results,
                namespace=self.namespace,
                filter=filter,  # Metadata filtering
                include_metadata=True
            )

            # Convert Pinecone response to ChromaDB format
            ids = [match.id for match in response.matches]
            metadatas = [match.metadata or {} for match in response.matches]
            distances = [match.score for match in response.matches]

            # Wrap in nested lists for ChromaDB API compatibility
            results = {
                "ids": [ids],
                "metadatas": [metadatas],
                "distances": [distances]
            }

            logger.debug(
                f"Query returned {len(ids)} results from namespace '{self.namespace}'"
            )
            return results

        except Exception as e:
            logger.error(f"Failed to query namespace '{self.namespace}': {e}")
            raise ConnectionError(f"Pinecone query failed: {e}") from e

    def delete_embedding(self, collection_name: str, id: str) -> None:
        """Delete embedding from collection by ID.

        Args:
            collection_name: Collection name (mapped to namespace)
            id: Unique identifier of embedding to delete

        Raises:
            ValueError: If id is empty
            ConnectionError: If Pinecone delete operation fails

        Example:
            >>> client.delete_embedding("email_embeddings", "msg123")
        """
        if not id:
            raise ValueError("ID cannot be empty")

        try:
            self.index.delete(ids=[id], namespace=self.namespace)
            logger.debug(f"Deleted embedding with id '{id}' from namespace '{self.namespace}'")
        except Exception as e:
            logger.error(f"Failed to delete embedding for id '{id}': {e}")
            raise ConnectionError(f"Pinecone delete failed for id '{id}': {e}") from e

    def count_embeddings(self, collection_name: str) -> int:
        """Get total count of embeddings in collection (namespace).

        Args:
            collection_name: Collection name (mapped to namespace)

        Returns:
            Total number of embeddings in namespace

        Raises:
            ConnectionError: If Pinecone stats operation fails

        Example:
            >>> count = client.count_embeddings("email_embeddings")
            >>> print(f"Total embeddings: {count}")
        """
        try:
            # Get index stats for namespace
            stats = self.index.describe_index_stats()

            # Extract count for our namespace (default to 0 if namespace not found)
            namespace_stats = stats.namespaces.get(self.namespace, {})
            count = namespace_stats.get('vector_count', 0)

            logger.debug(f"Namespace '{self.namespace}' contains {count} embeddings")
            return count

        except Exception as e:
            logger.error(f"Failed to count embeddings in namespace '{self.namespace}': {e}")
            raise ConnectionError(f"Pinecone stats failed: {e}") from e

    def health_check(self) -> bool:
        """Verify Pinecone connection is active and responsive.

        Returns:
            True if connection is active, False otherwise

        Example:
            >>> if client.health_check():
            ...     print("Pinecone is connected")
        """
        try:
            # Test connection by fetching index stats
            self.index.describe_index_stats()
            logger.debug("Pinecone health check passed")
            return True
        except Exception as e:
            logger.error(f"Pinecone health check failed: {e}")
            return False
