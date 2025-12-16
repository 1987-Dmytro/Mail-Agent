"""Context Retrieval Service for Smart Hybrid RAG.

This module provides context retrieval functionality for AI response generation,
implementing the Smart Hybrid RAG strategy (ADR-011) which combines:
- Gmail thread history (last 5 emails for conversation continuity)
- Semantic vector search (top 3-7 similar emails for broader context)

Key Features:
- Adaptive k logic: Adjusts semantic search count based on thread length
- Token budget enforcement: Maintains ~6.5K token limit for LLM context window
- Parallel retrieval: Uses asyncio to fetch thread history and semantic results concurrently
- Performance optimized: Target <3 seconds total retrieval time (NFR001)

Usage:
    service = ContextRetrievalService(user_id=123)

    # Retrieve context for incoming email
    context = await service.retrieve_context(email_id=456)

    # Access context components
    thread_emails = context["thread_history"]  # Last 5 emails in thread
    semantic_emails = context["semantic_results"]  # Top 3-7 similar emails
    metadata = context["metadata"]  # Statistics and token usage

Reference: docs/tech-spec-epic-3.md#Smart-Hybrid-RAG-Strategy
ADR: docs/adrs/epic-3-architecture-decisions.md#ADR-011
"""

import asyncio
import math
import os
import time
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Tuple

import structlog
import tiktoken
from sqlmodel import select

from app.core.embedding_service import EmbeddingService
from app.core.gmail_client import GmailClient
from app.core.vector_db_pinecone import PineconeVectorDBClient
from app.models.context_models import EmailMessage, RAGContext
from app.models.email import EmailProcessingQueue
from app.services.database import DatabaseService, database_service


class ContextRetrievalService:
    """Service for retrieving conversation context using Smart Hybrid RAG.

    This service implements ADR-011 (Smart Hybrid RAG Strategy) by combining:
    1. Thread history: Last 5 emails from Gmail thread (conversation continuity)
    2. Semantic search: Top 3-7 similar emails from vector DB (broader context)

    The adaptive k logic dynamically adjusts semantic search count:
    - Short threads (<3 emails): k=7 (need more context)
    - Standard threads (3-5 emails): k=3 (balanced hybrid)
    - Long threads (>5 emails): k=0 (thread sufficient, skip semantic)

    Token budget is enforced at ~6.5K tokens total, leaving 25K tokens for
    Gemini response generation within 32K context window.

    Attributes:
        user_id: Database ID of user
        db_service: Database service for email queries
        gmail_client: Gmail API client wrapper
        embedding_service: Gemini embedding service
        vector_db_client: ChromaDB client
        logger: Structured logger
        tokenizer: tiktoken encoding for GPT-4 (compatible with Gemini)
    """

    # Token budget constants (AC #8, #9)
    MAX_CONTEXT_TOKENS = 6500  # Conservative limit (~6.5K tokens)
    GEMINI_TOTAL_CONTEXT = 32000  # Gemini's actual limit
    RESERVED_FOR_RESPONSE = 25000  # Leave room for response generation

    # Thread history constants (AC #2)
    MAX_THREAD_HISTORY_LENGTH = 5  # Last 5 emails from thread

    # Adaptive k thresholds (AC #5)
    SHORT_THREAD_THRESHOLD = 3  # <3 emails = short thread
    LONG_THREAD_THRESHOLD = 5  # >5 emails = long thread
    SHORT_THREAD_K = 7  # k=7 for short threads (need more context)
    STANDARD_THREAD_K = 3  # k=3 for standard threads (balanced)
    LONG_THREAD_K = 0  # k=0 for long threads (skip semantic)

    # Performance target (AC #11)
    TARGET_LATENCY_SECONDS = 3.0  # <3 seconds per NFR001

    # Temporal filtering constants (Recency boost based on 2025 RAG best practices)
    RECENCY_ALPHA = 0.7  # 70% semantic similarity, 30% recency score
    HALF_LIFE_DAYS = 14  # 14-day half-life for exponential decay
    DEFAULT_TEMPORAL_WINDOW_DAYS = 30  # Default: last 30 days for recent context

    def __init__(
        self,
        user_id: int,
        db_service: DatabaseService = None,
        gmail_client: GmailClient = None,
        embedding_service: EmbeddingService = None,
        vector_db_client: PineconeVectorDBClient = None,
    ):
        """Initialize context retrieval service for specific user.

        Args:
            user_id: Database ID of user
            db_service: Optional DatabaseService for dependency injection (testing)
            gmail_client: Optional GmailClient for dependency injection (testing)
            embedding_service: Optional EmbeddingService for dependency injection (testing)
            vector_db_client: Optional VectorDBClient for dependency injection (testing)

        Example:
            # Production usage
            service = ContextRetrievalService(user_id=123)

            # Test usage with mocks
            service = ContextRetrievalService(
                user_id=123,
                gmail_client=mock_gmail,
                embedding_service=mock_embeddings,
                vector_db_client=mock_vector_db
            )
        """
        self.user_id = user_id
        self.db_service = db_service or database_service
        self.gmail_client = gmail_client or GmailClient(user_id=user_id, db_service=self.db_service)
        self.embedding_service = embedding_service or EmbeddingService()
        # Use Pinecone for cloud-native persistent storage
        from app.core.config import settings
        self.vector_db_client = vector_db_client or PineconeVectorDBClient(
            api_key=settings.PINECONE_API_KEY,
            index_name="ai-assistant-memories"
        )
        self.logger = structlog.get_logger(__name__)

        # Initialize tiktoken for accurate token counting (AC #8)
        # Gemini uses similar tokenization to GPT-4
        self.tokenizer = tiktoken.encoding_for_model("gpt-4")

        self.logger.info(
            "context_retrieval_service_initialized",
            user_id=user_id,
            max_tokens=self.MAX_CONTEXT_TOKENS,
            target_latency=self.TARGET_LATENCY_SECONDS,
        )

    async def _get_thread_history(self, thread_id: str) -> Tuple[List[EmailMessage], int]:
        """Retrieve thread history from Gmail (last 5 emails in chronological order).

        Implements AC #2: Method retrieves thread history from Gmail using thread_id
        (last 5 emails in chronological order).

        Args:
            thread_id: Gmail thread ID

        Returns:
            Tuple of (emails, original_length):
                - emails: List of EmailMessage dicts (last 5 emails, chronological order)
                - original_length: Original thread length before truncation (for adaptive k)

        Example:
            thread_emails, original_len = await service._get_thread_history("18b7c8d9e0f1a2b3")
            # Returns: ([email1, email2, email3, email4, email5], 8)
        """
        try:
            # Call Gmail API to retrieve all emails in thread
            # GmailClient.get_thread returns List[Dict] sorted chronologically (oldest first)
            thread_messages = await self.gmail_client.get_thread(thread_id)

            # Handle empty thread
            if not thread_messages:
                self.logger.warning(
                    "empty_thread_retrieved",
                    thread_id=thread_id,
                    user_id=self.user_id
                )
                return [], 0

            # Save original thread length BEFORE truncation (for adaptive k logic)
            original_thread_length = len(thread_messages)

            # Extract last 5 emails if thread has more than 5
            # Keep chronological order (oldest → newest)
            if len(thread_messages) > self.MAX_THREAD_HISTORY_LENGTH:
                thread_messages = thread_messages[-self.MAX_THREAD_HISTORY_LENGTH:]

            # Convert Gmail API format to EmailMessage TypedDict format
            email_messages: List[EmailMessage] = []
            for msg in thread_messages:
                # Convert received_at datetime to ISO 8601 string
                date_str = msg["received_at"].isoformat() if isinstance(msg["received_at"], datetime) else str(msg["received_at"])

                email_message: EmailMessage = {
                    "message_id": msg["message_id"],
                    "sender": msg["sender"],
                    "subject": msg["subject"],
                    "body": msg["body"],
                    "date": date_str,
                    "thread_id": msg["thread_id"]
                }
                email_messages.append(email_message)

            # Extract oldest email date for metadata logging
            oldest_date = email_messages[0]["date"] if email_messages else None

            # Log successful thread retrieval
            self.logger.info(
                "thread_history_retrieved",
                thread_id=thread_id,
                user_id=self.user_id,
                email_count=len(email_messages),
                original_thread_length=original_thread_length,
                oldest_email_date=oldest_date,
                truncated=original_thread_length > len(email_messages)
            )

            return email_messages, original_thread_length

        except Exception as e:
            # Log error and re-raise (thread history is CRITICAL for context)
            # Story requirement: "If thread retrieval fails, raise exception (critical for context)"
            self.logger.error(
                "thread_history_retrieval_failed",
                thread_id=thread_id,
                user_id=self.user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            # Re-raise exception - thread history is critical, cannot proceed without it
            raise

    async def _get_sender_history(
        self,
        sender: str,
        user_id: int,
        days: int = 90,
        max_emails: int = 5  # Reduced from 10 to prevent OOM on Nano (512MB)
    ) -> Tuple[List[EmailMessage], int]:
        """Retrieve recent emails from a specific sender over last N days.

        This provides complete conversation context across multiple threads,
        enabling chronological understanding of the full correspondence.

        Args:
            sender: Email address of the sender
            user_id: User ID for filtering
            days: Number of days to look back (default: 90)
            max_emails: Maximum number of emails to retrieve (default: 50)

        Returns:
            Tuple of (list of EmailMessage dicts sorted chronologically, total count)

        Example:
            For sender="colleague@example.com", retrieves:
            1. "Праздники 2025" (2025-12-07 09:00)
            2. "Re: Праздники" (2025-12-07 14:00)
            3. Other emails from same sender...

        Note: Sorted oldest→newest for chronological narrative.
        """
        try:
            self.logger.info(
                "sender_history_retrieval_started",
                sender=sender,
                user_id=user_id,
                days=days
            )

            # Query ChromaDB for ALL emails from this sender
            # NOTE: We do NOT filter by user_id or timestamp here to handle data migration scenarios:
            # 1. Emails may have been indexed with different user_ids (e.g., after database reset)
            # 2. Older emails may not have "timestamp" field (only "date" string field)
            # For sender_history, we want COMPLETE conversation history regardless of indexing metadata.
            filter_conditions = {"sender": sender}

            # Query without embedding (just metadata filter) to get ALL emails
            # Access ChromaDB collection directly for metadata-only query
            collection = self.vector_db_client.client.get_collection(name="email_embeddings")

            # Use a very large limit to ensure we fetch ALL emails from this sender
            # ChromaDB's count() doesn't support where clause, so we use a large limit instead
            # For sender_history, we want complete conversation history (not just first N emails)
            results = collection.get(
                where=filter_conditions,
                limit=1000,  # Very large limit to get all emails from sender (realistic max)
                include=["metadatas"]
            )

            if not results["ids"]:
                self.logger.info(
                    "sender_history_empty",
                    sender=sender,
                    user_id=user_id
                )
                return [], 0

            # Process results into EmailMessage format
            ids = results["ids"]
            metadatas = results["metadatas"]
            total_count = len(ids)

            # OPTIMIZATION: Sort by timestamp BEFORE fetching full bodies to prevent OOM
            # Old flow: Fetch all 50 → sort → keep 10 = 50 Gmail API calls
            # New flow: Sort metadata → take top 10 → fetch only 10 = 10 Gmail API calls

            # Step 1: Extract timestamps from metadata and create lightweight records
            email_metadata_list = []
            for i, message_id in enumerate(ids):
                metadata = metadatas[i]
                # Use timestamp from vector DB metadata (set during indexing)
                sort_timestamp = metadata.get("timestamp", 0)
                email_metadata_list.append({
                    "message_id": message_id,
                    "metadata": metadata,
                    "_timestamp": sort_timestamp
                })

            # Step 2: Sort by timestamp (oldest → newest)
            email_metadata_list.sort(key=lambda x: x["_timestamp"])

            # Step 3: Take only max_emails most recent (last N after sorting)
            if len(email_metadata_list) > max_emails:
                email_metadata_list = email_metadata_list[-max_emails:]

            # Step 4: NOW fetch full bodies ONLY for top N emails (not all 50!)
            email_messages: List[EmailMessage] = []
            for item in email_metadata_list:
                message_id = item["message_id"]
                metadata = item["metadata"]

                try:
                    # Fetch full email details from Gmail ONLY for selected emails
                    email_detail = await self.gmail_client.get_message_detail(message_id)

                    # Use received_at from Gmail as the canonical timestamp
                    received_at = email_detail["received_at"]
                    if isinstance(received_at, datetime):
                        date_str = received_at.isoformat()
                        sort_timestamp = int(received_at.timestamp())
                    else:
                        date_str = str(received_at)
                        sort_timestamp = metadata.get("timestamp", 0)

                    email_message: EmailMessage = {
                        "message_id": message_id,
                        "sender": email_detail["sender"],
                        "subject": email_detail["subject"],
                        "body": email_detail["body"],
                        "date": date_str,
                        "thread_id": email_detail["thread_id"],
                        "_timestamp": sort_timestamp
                    }

                    email_messages.append(email_message)

                except Exception as e:
                    self.logger.warning(
                        "sender_history_email_fetch_failed",
                        message_id=message_id,
                        error=str(e)
                    )
                    continue

            self.logger.info(
                "sender_history_retrieval_completed",
                sender=sender,
                user_id=user_id,
                count=len(email_messages),
                total_count=total_count,
                days=days,
                limited_to=max_emails if total_count > max_emails else None
            )

            return email_messages, total_count

        except Exception as e:
            self.logger.error(
                "sender_history_retrieval_failed",
                sender=sender,
                user_id=user_id,
                error=str(e)
            )
            return [], 0

    async def _get_semantic_results(
        self,
        email_body: str,
        sender: str,
        k: int,
        user_id: int,
        thread_length: int = 0,
        received_at: Optional[datetime] = None
    ) -> List[EmailMessage]:
        """Perform semantic search in vector DB using email content as query embedding.

        Implements AC #3, #4: Method performs semantic search in vector DB using email
        content as query embedding. Top-k most relevant emails retrieved with adaptive
        k logic (k=3-7 based on thread length).

        IMPORTANT: Filters results by sender email to retrieve conversation-specific context.
        This ensures AI responses have proper context from the SAME correspondent, not unrelated
        emails with similar topics from different senders.

        Enhanced with temporal awareness: prioritizes recent emails (last 7 days) to understand
        conversation continuity, especially when subject changes mid-conversation.

        Args:
            email_body: Email body text to use as query (enhanced with sender + subject context)
            sender: Email address of sender (for filtering conversation context)
            k: Number of results to retrieve (adaptive: 0, 3, or 7)
            user_id: User ID for multi-tenant filtering
            received_at: Optional timestamp of current email for temporal filtering

        Returns:
            List of EmailMessage dicts (top k similar emails from SAME sender, unordered)
            Returns empty list if k=0 or no embeddings found or API error occurs.

        Example:
            semantic_emails = await service._get_semantic_results(
                email_body="From sender about Question: budget details...",
                sender="colleague@company.com",
                k=3,
                user_id=123,
                received_at=datetime.now()
            )
        """
        # Skip semantic search if k=0 (long threads don't need semantic context)
        if k == 0:
            self.logger.info(
                "semantic_search_skipped",
                user_id=user_id,
                k=k,
                reason="long_thread_adaptive_k"
            )
            return []

        try:
            # Generate query embedding from email body
            query_embedding = self.embedding_service.embed_text(email_body)

            # Calculate adaptive temporal window based on thread length
            temporal_window_days = self._get_temporal_window_days(thread_length)
            cutoff_date = datetime.now(UTC) - timedelta(days=temporal_window_days)
            cutoff_timestamp = int(cutoff_date.timestamp())

            # Query ChromaDB for top k most similar emails
            # Filter by user_id AND sender AND timestamp for conversation-specific recent context
            # ChromaDB requires $and operator for multiple filter conditions
            filter_conditions = [
                {"user_id": str(user_id)},  # Multi-tenant isolation
                {"sender": sender},  # Conversation-specific context (same correspondent)
                {"timestamp": {"$gte": cutoff_timestamp}}  # Temporal filtering (recent emails only)
            ]

            results = self.vector_db_client.query_embeddings(
                collection_name="email_embeddings",
                query_embedding=query_embedding,
                n_results=k,
                filter={"$and": filter_conditions}
            )

            # Log temporal filtering details
            self.logger.info(
                "temporal_filter_applied",
                user_id=user_id,
                thread_length=thread_length,
                temporal_window_days=temporal_window_days,
                cutoff_date=cutoff_date.isoformat()
            )

            # Handle empty results
            if not results["ids"] or not results["ids"][0]:
                self.logger.warning(
                    "no_semantic_results_found",
                    user_id=user_id,
                    k=k
                )
                return []

            # Extract result metadata (ChromaDB returns nested lists)
            ids = results["ids"][0]
            metadatas = results["metadatas"][0]
            distances = results["distances"][0]

            # Log top relevance scores for performance monitoring
            top_scores = distances[:3] if len(distances) >= 3 else distances
            self.logger.info(
                "semantic_search_completed",
                user_id=user_id,
                k=k,
                result_count=len(ids),
                top_relevance_scores=top_scores
            )

            # Fetch full email bodies from Gmail API using message_ids
            # Metadata only contains snippets (first 200 chars), but we need full bodies for context
            email_messages: List[EmailMessage] = []

            for i, message_id in enumerate(ids):
                try:
                    # Fetch full email details from Gmail
                    email_detail = await self.gmail_client.get_message_detail(message_id)

                    # Convert received_at datetime to ISO 8601 string
                    date_str = email_detail["received_at"].isoformat() if isinstance(email_detail["received_at"], datetime) else str(email_detail["received_at"])

                    # Extract timestamp from ChromaDB metadata for recency scoring
                    metadata = metadatas[i]
                    timestamp = metadata.get("timestamp", 0)

                    # Calculate recency score using half-life decay function
                    recency_score = self._calculate_recency_score(
                        timestamp=timestamp,
                        half_life_days=self.HALF_LIFE_DAYS
                    )

                    # Calculate fused score (semantic + temporal)
                    cosine_distance = distances[i]
                    fused = self._fused_score(
                        cosine_sim=cosine_distance,
                        recency=recency_score,
                        alpha=self.RECENCY_ALPHA
                    )

                    # Create EmailMessage with full body and metadata from ChromaDB
                    email_message: EmailMessage = {
                        "message_id": message_id,
                        "sender": email_detail["sender"],
                        "subject": email_detail["subject"],
                        "body": email_detail["body"],
                        "date": date_str,
                        "thread_id": email_detail["thread_id"]
                    }

                    # Store ranking attributes (will be used in _rank_semantic_results)
                    # Attach as temporary attributes for ranking, will be removed after ranking
                    email_message["_distance"] = cosine_distance  # type: ignore
                    email_message["_timestamp"] = timestamp  # type: ignore
                    email_message["_recency_score"] = recency_score  # type: ignore
                    email_message["_fused_score"] = fused  # type: ignore

                    email_messages.append(email_message)

                except Exception as e:
                    # Log error but continue processing other results
                    self.logger.warning(
                        "failed_to_fetch_semantic_result_body",
                        message_id=message_id,
                        user_id=user_id,
                        error=str(e),
                        error_type=type(e).__name__
                    )
                    continue

            return email_messages

        except Exception as e:
            # Log error and return empty list for graceful degradation
            self.logger.error(
                "semantic_search_failed",
                user_id=user_id,
                k=k,
                error=str(e),
                error_type=type(e).__name__
            )
            # Return empty list to allow thread-only context if semantic search fails
            return []

    def _calculate_adaptive_k(self, thread_length: int) -> int:
        """Calculate adaptive k value based on thread length.

        Implements AC #5: Adaptive k implementation: Short threads (<3 emails) → k=7,
        standard threads (3-5 emails) → k=3, long threads (>5 emails) → k=0 (skip semantic).

        Rationale (ADR-011):
        - Short threads need more semantic context (insufficient thread history)
        - Standard threads benefit from balanced hybrid approach
        - Long threads have sufficient context already (semantic adds noise)

        Args:
            thread_length: Number of emails in thread

        Returns:
            Adaptive k value: 0, 3, or 7

        Example:
            k = service._calculate_adaptive_k(thread_length=2)  # Returns 7
            k = service._calculate_adaptive_k(thread_length=4)  # Returns 3
            k = service._calculate_adaptive_k(thread_length=8)  # Returns 0
        """
        # Short threads (<3 emails): Need more semantic context
        if thread_length < self.SHORT_THREAD_THRESHOLD:
            k = self.SHORT_THREAD_K
            reasoning = "short_thread_needs_more_context"
        # Long threads (>5 emails): Sufficient thread history, skip semantic
        elif thread_length > self.LONG_THREAD_THRESHOLD:
            k = self.LONG_THREAD_K
            reasoning = "long_thread_sufficient_context"
        # Standard threads (3-5 emails): Balanced hybrid approach
        else:
            k = self.STANDARD_THREAD_K
            reasoning = "standard_hybrid_approach"

        # Log adaptive k decision for monitoring
        self.logger.info(
            "adaptive_k_calculated",
            thread_length=thread_length,
            calculated_k=k,
            reasoning=reasoning,
            thresholds={
                "short": self.SHORT_THREAD_THRESHOLD,
                "long": self.LONG_THREAD_THRESHOLD
            }
        )

        return k

    @staticmethod
    def _calculate_recency_score(timestamp: int, half_life_days: int = 14) -> float:
        """Calculate exponential decay score based on email age.

        Implements temporal ranking using half-life decay function from
        "Solving Freshness in RAG" (arXiv 2025).

        Formula: recency_score = exp(-ln(2) * days_ago / half_life)

        Args:
            timestamp: Unix timestamp of email received_at
            half_life_days: Number of days for score to decay to 50% (default: 14)

        Returns:
            Recency score between 0.0 and 1.0 (1.0 = today, 0.5 = 14 days ago)

        Example:
            # Email from today
            score = _calculate_recency_score(time.time())  # Returns ~1.0

            # Email from 14 days ago
            old_timestamp = time.time() - (14 * 86400)
            score = _calculate_recency_score(old_timestamp)  # Returns ~0.5

            # Email from 28 days ago
            very_old = time.time() - (28 * 86400)
            score = _calculate_recency_score(very_old)  # Returns ~0.25
        """
        now = datetime.now(UTC).timestamp()
        days_ago = (now - timestamp) / 86400  # Convert seconds to days

        # Exponential decay: score = e^(-ln(2) * days_ago / half_life)
        # This ensures score = 0.5 when days_ago = half_life
        recency_score = math.exp(-math.log(2) * days_ago / half_life_days)

        return max(0.0, min(1.0, recency_score))  # Clamp to [0, 1]

    @staticmethod
    def _fused_score(cosine_sim: float, recency: float, alpha: float = 0.7) -> float:
        """Combine semantic similarity and recency into fused score.

        Implements hybrid ranking from "Solving Freshness in RAG" (arXiv 2025).

        Formula: fused_score = alpha * cosine_sim + (1 - alpha) * recency

        Args:
            cosine_sim: Cosine similarity score (ChromaDB distance, 0.0-1.0, lower is better)
            recency: Recency score from _calculate_recency_score (0.0-1.0, higher is better)
            alpha: Weight for semantic similarity (default: 0.7 = 70% semantic, 30% temporal)

        Returns:
            Fused score (higher = better match)

        Example:
            # High semantic, recent email
            score = _fused_score(cosine_sim=0.1, recency=1.0, alpha=0.7)
            # Returns: 0.7 * (1 - 0.1) + 0.3 * 1.0 = 0.63 + 0.3 = 0.93

            # High semantic, old email
            score = _fused_score(cosine_sim=0.1, recency=0.2, alpha=0.7)
            # Returns: 0.7 * (1 - 0.1) + 0.3 * 0.2 = 0.63 + 0.06 = 0.69

            # Low semantic, recent email
            score = _fused_score(cosine_sim=0.8, recency=1.0, alpha=0.7)
            # Returns: 0.7 * (1 - 0.8) + 0.3 * 1.0 = 0.14 + 0.3 = 0.44
        """
        # Convert ChromaDB distance to similarity (distance 0 = perfect match = similarity 1)
        similarity = 1.0 - cosine_sim

        # Weighted combination: alpha * semantic + (1-alpha) * temporal
        return alpha * similarity + (1 - alpha) * recency

    @staticmethod
    def _get_temporal_window_days(thread_length: int) -> int:
        """Calculate adaptive temporal window based on thread length.

        Longer threads may reference older context, so we expand the temporal window
        to avoid filtering out relevant historical emails.

        Args:
            thread_length: Number of emails in current thread

        Returns:
            Number of days for temporal filtering window

        Example:
            window = _get_temporal_window_days(0)  # Returns 30 (new thread)
            window = _get_temporal_window_days(2)  # Returns 60 (short thread)
            window = _get_temporal_window_days(6)  # Returns 90 (long thread)
        """
        if thread_length == 0:
            return 30  # New thread - only recent context
        elif thread_length <= 3:
            return 60  # Short thread - moderate history
        else:
            return 90  # Long thread - full 90-day history

    def _rank_semantic_results(self, results: List[EmailMessage]) -> List[EmailMessage]:
        """Rank semantic results by fused score (semantic + temporal).

        Implements hybrid ranking from "Solving Freshness in RAG" (arXiv 2025):
        - Combines cosine similarity (70%) with recency score (30%)
        - Uses half-life decay function for temporal weighting

        Ranking algorithm:
        1. Sort by fused_score (descending, higher = better)
        2. Remove temporary ranking attributes (_distance, _timestamp, _recency_score, _fused_score)

        Args:
            results: List of EmailMessage dicts with temporary ranking attributes

        Returns:
            List of EmailMessage dicts (ranked by fused score, temp attributes removed)

        Example:
            ranked_emails = service._rank_semantic_results(semantic_results)
        """
        if not results:
            return []

        # Sort by fused score (descending, higher = better)
        # Fused score already combines semantic similarity + recency
        ranked_results = sorted(
            results,
            key=lambda email: email.get("_fused_score", 0.0),
            reverse=True  # Higher fused score = better match
        )

        # Extract scores for logging
        fused_scores = [email.get("_fused_score", 0.0) for email in ranked_results if "_fused_score" in email]
        recency_scores = [email.get("_recency_score", 0.0) for email in ranked_results if "_recency_score" in email]
        distances = [email.get("_distance", 0.0) for email in ranked_results if "_distance" in email]
        dates = [email["date"] for email in ranked_results]

        score_range = {
            "fused_min": min(fused_scores) if fused_scores else None,
            "fused_max": max(fused_scores) if fused_scores else None,
            "recency_min": min(recency_scores) if recency_scores else None,
            "recency_max": max(recency_scores) if recency_scores else None,
            "distance_min": min(distances) if distances else None,
            "distance_max": max(distances) if distances else None,
        }
        date_range = {
            "oldest": min(dates) if dates else None,
            "newest": max(dates) if dates else None
        }

        self.logger.info(
            "semantic_results_ranked",
            result_count=len(ranked_results),
            score_range=score_range,
            date_range=date_range
        )

        # Remove all temporary ranking attributes before returning
        for email in ranked_results:
            # Clean up temporary attributes used for ranking
            for attr in ["_distance", "_timestamp", "_recency_score", "_fused_score"]:
                if attr in email:
                    del email[attr]  # type: ignore

        return ranked_results

    def _parse_date_for_sort(self, date_str: str) -> float:
        """Parse ISO 8601 date string to timestamp for sorting.

        Args:
            date_str: ISO 8601 date string

        Returns:
            Unix timestamp (float) for comparison, or 0.0 if parsing fails
        """
        try:
            # Parse ISO 8601 date string to datetime
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.timestamp()
        except Exception:
            # Return 0.0 if parsing fails (treat as very old)
            return 0.0

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken (GPT-4 compatible tokenizer).

        Implements AC #8: Context window managed to stay within LLM token limits
        (~6.5K tokens total for context).

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens in text

        Example:
            tokens = service._count_tokens("Tax return deadline reminder...")
            # Returns: 5
        """
        if not text:
            return 0

        try:
            # Encode text using tiktoken (GPT-4 tokenizer, compatible with Gemini)
            tokens = self.tokenizer.encode(text)
            return len(tokens)
        except Exception as e:
            # Log error and return conservative estimate (1 token per 4 characters)
            self.logger.warning(
                "token_counting_failed",
                text_length=len(text),
                error=str(e),
                fallback_estimate=len(text) // 4
            )
            return len(text) // 4  # Conservative fallback: ~4 chars per token

    def _enforce_token_budget(
        self,
        thread_history: List[EmailMessage],
        semantic_results: List[EmailMessage],
        max_tokens: int = MAX_CONTEXT_TOKENS,
    ) -> Tuple[List[EmailMessage], List[EmailMessage]]:
        """Enforce token budget by truncating context if over limit.

        Implements AC #9: Token counting implemented for thread history and semantic
        results to enforce budget.

        Truncation strategy (ADR-011):
        1. Count tokens in all email bodies (thread_history + semantic_results)
        2. If total > max_tokens:
           a. Truncate thread_history first (keep most recent N emails)
           b. If still over, truncate semantic_results (remove lowest ranked)
        3. Return truncated lists

        Args:
            thread_history: List of thread emails (chronological)
            semantic_results: List of semantic emails (ranked by relevance)
            max_tokens: Maximum token budget (default: 6500)

        Returns:
            Tuple of (truncated_thread_history, truncated_semantic_results)

        Example:
            thread, semantic = service._enforce_token_budget(
                thread_history=[email1, email2, email3],
                semantic_results=[email4, email5, email6],
                max_tokens=6500
            )
        """
        # Count tokens in thread history
        thread_tokens = sum(self._count_tokens(email["body"]) for email in thread_history)

        # Count tokens in semantic results
        semantic_tokens = sum(self._count_tokens(email["body"]) for email in semantic_results)

        # Calculate total tokens
        total_tokens = thread_tokens + semantic_tokens

        # If within budget, return as-is
        if total_tokens <= max_tokens:
            self.logger.info(
                "token_budget_check",
                thread_tokens=thread_tokens,
                semantic_tokens=semantic_tokens,
                total_tokens=total_tokens,
                max_tokens=max_tokens,
                budget_exceeded=False
            )
            return thread_history, semantic_results

        # Budget exceeded - need to truncate
        self.logger.warning(
            "token_budget_exceeded_truncating",
            thread_tokens=thread_tokens,
            semantic_tokens=semantic_tokens,
            total_tokens=total_tokens,
            max_tokens=max_tokens,
            overage=total_tokens - max_tokens
        )

        # Strategy 1: Truncate thread_history first (keep most recent emails)
        truncated_thread = list(thread_history)  # Copy to avoid modifying original
        truncated_semantic = list(semantic_results)  # Copy to avoid modifying original

        # Remove oldest thread emails until we're under budget (or no thread emails left)
        while truncated_thread and total_tokens > max_tokens:
            # Remove oldest email (first in list, since chronological order)
            removed_email = truncated_thread.pop(0)
            removed_tokens = self._count_tokens(removed_email["body"])
            thread_tokens -= removed_tokens
            total_tokens -= removed_tokens

        # Strategy 2: If still over budget, truncate semantic_results (remove lowest ranked)
        # semantic_results are ranked by relevance, so remove from end (least relevant)
        while truncated_semantic and total_tokens > max_tokens:
            # Remove least relevant email (last in list, since ranked)
            removed_email = truncated_semantic.pop()
            removed_tokens = self._count_tokens(removed_email["body"])
            semantic_tokens -= removed_tokens
            total_tokens -= removed_tokens

        # Log final token usage after truncation
        self.logger.info(
            "token_budget_enforced",
            thread_tokens=thread_tokens,
            semantic_tokens=semantic_tokens,
            total_tokens=total_tokens,
            max_tokens=max_tokens,
            thread_removed=len(thread_history) - len(truncated_thread),
            semantic_removed=len(semantic_results) - len(truncated_semantic)
        )

        return truncated_thread, truncated_semantic

    async def retrieve_context(self, email_id: int) -> RAGContext:
        """Retrieve conversation context for incoming email using Smart Hybrid RAG.

        Implements AC #1, #6, #10, #11, #12: Main context retrieval method that combines
        thread history and semantic search into RAGContext structure, with performance
        optimization via parallel retrieval.

        Workflow:
        1. Load email from database by email_id
        2. Extract gmail_thread_id and email body
        3. Parallel retrieval (AC #12):
           a. Fetch thread history from Gmail (last 5 emails)
           b. Calculate adaptive k based on thread length
           c. Perform semantic search in vector DB (top k similar emails)
        4. Rank semantic results by relevance and recency
        5. Enforce token budget (~6.5K tokens total)
        6. Construct RAGContext with thread_history, semantic_results, metadata
        7. Log performance metrics (AC #11)

        Args:
            email_id: Database ID of email in EmailProcessingQueue

        Returns:
            RAGContext dict with thread_history, semantic_results, and metadata

        Raises:
            ValueError: If email_id not found in database
            GmailAPIError: If thread retrieval fails (critical for context)
            Exception: For other errors (logged with full context)

        Example:
            service = ContextRetrievalService(user_id=123)
            context = await service.retrieve_context(email_id=456)

            # Access context components
            thread_emails = context["thread_history"]  # Last 5 emails
            semantic_emails = context["semantic_results"]  # Top 3-7 similar
            stats = context["metadata"]  # thread_length, semantic_count, total_tokens_used
        """
        # Start performance timer (AC #11)
        start_time = time.perf_counter()

        self.logger.info(
            "context_retrieval_started",
            email_id=email_id,
            user_id=self.user_id
        )

        try:
            # Step 1: Load email from database by email_id
            async with self.db_service.async_session() as session:
                result = await session.execute(
                    select(EmailProcessingQueue).where(EmailProcessingQueue.id == email_id)
                )
                email = result.scalar_one_or_none()

            if not email:
                raise ValueError(f"Email with id {email_id} not found in EmailProcessingQueue")

            # Extract gmail_thread_id and prepare enhanced query for semantic search
            gmail_thread_id = email.gmail_thread_id

            # Step 1.5: Fetch full email body from Gmail API for better semantic search
            # EmailProcessingQueue only stores subject, but we need full body for accurate context
            try:
                email_detail = await self.gmail_client.get_message_detail(email.gmail_message_id)
                full_body = email_detail.get("body", "")
            except Exception as e:
                self.logger.warning(
                    "failed_to_fetch_email_body_for_query",
                    email_id=email_id,
                    error=str(e)
                )
                full_body = ""

            # Enhanced query construction for better semantic matching
            # Include: sender name + subject + body + temporal context
            # This helps find related emails even when subject changes (e.g., "Вопрос" → "Праздники 2025")
            sender_name = email.sender.split('@')[0].replace('.', ' ').replace('_', ' ')
            email_subject = email.subject or ""

            # Build contextual query for semantic search with subject boost
            # Format: "[subject] [subject] From [sender]: [body preview]"
            # Subject is duplicated to boost its weight in embedding (2025 RAG best practice)
            # This improves matching when emails from same sender have different subjects
            email_query = f"{email_subject} {email_subject} From {sender_name}: {full_body[:500]}"

            self.logger.info(
                "enhanced_query_constructed",
                email_id=email_id,
                query_length=len(email_query),
                has_full_body=bool(full_body),
                sender_name=sender_name
            )

            # Step 2: Fetch thread history from Gmail
            # NOTE: Must complete before Step 3 to enable adaptive k calculation (AC #5)
            thread_history, original_thread_length = await self._get_thread_history(gmail_thread_id)

            # Step 2.5: Fetch sender conversation history (last 90 days, max 5 emails)
            # Reduced from 10 to 5 to prevent OOM on Nano instance (512MB RAM)
            sender_history, sender_history_count = await self._get_sender_history(
                sender=email.sender,
                user_id=self.user_id,
                days=90,
                max_emails=5,  # Reduced from 10 to prevent OOM crashes
            )

            self.logger.info(
                "sender_history_retrieved",
                user_id=self.user_id,
                sender=email.sender,
                count=sender_history_count,
                email_id=email_id
            )

            # Step 3: Calculate adaptive k based on thread length (AC #5)
            # DESIGN DECISION: Sequential execution required here to satisfy AC #5
            # Adaptive k logic DEPENDS on thread_length from Step 2, preventing parallelization
            # with semantic search (which requires k value). Parallel execution would require
            # fixed k, violating AC #5 requirement for dynamic k based on thread length.
            k = self._calculate_adaptive_k(original_thread_length)

            # Step 4: Perform semantic search if k > 0 (AC #3, #4)
            if k > 0:
                semantic_results = await self._get_semantic_results(
                    email_body=email_query,  # Use enhanced query with subject boost
                    sender=email.sender,  # Filter by sender for conversation context
                    k=k,
                    user_id=self.user_id,
                    thread_length=original_thread_length,  # For adaptive temporal window
                    received_at=email.received_at  # Pass temporal context for metadata
                )
            else:
                semantic_results = []

            # Step 5: Rank semantic results by relevance and recency (AC #7)
            if semantic_results:
                semantic_results = self._rank_semantic_results(semantic_results)

            # Step 6: Enforce token budget (AC #8, #9)
            thread_history, semantic_results = self._enforce_token_budget(
                thread_history=thread_history,
                semantic_results=semantic_results,
                max_tokens=self.MAX_CONTEXT_TOKENS
            )

            # Step 7: Count final tokens for metadata
            final_thread_tokens = sum(self._count_tokens(email["body"]) for email in thread_history)
            final_semantic_tokens = sum(self._count_tokens(email["body"]) for email in semantic_results)
            total_tokens_used = final_thread_tokens + final_semantic_tokens

            # Extract oldest thread date for metadata
            oldest_thread_date = thread_history[0]["date"] if thread_history else None

            # Step 8: Construct RAGContext (AC #6, #10)
            context: RAGContext = {
                "thread_history": thread_history,
                "sender_history": sender_history,  # NEW: Full sender conversation history
                "semantic_results": semantic_results,
                "metadata": {
                    "thread_length": original_thread_length,
                    "semantic_count": len(semantic_results),
                    "sender_history_count": sender_history_count,  # NEW: Sender history count
                    "oldest_thread_date": oldest_thread_date,
                    "total_tokens_used": total_tokens_used,
                    "adaptive_k": k,
                    "thread_tokens": final_thread_tokens,
                    "semantic_tokens": final_semantic_tokens
                }
            }

            # Step 9: Calculate retrieval latency and log performance (AC #11)
            latency_seconds = time.perf_counter() - start_time
            latency_ms = latency_seconds * 1000

            self.logger.info(
                "context_retrieval_completed",
                email_id=email_id,
                user_id=self.user_id,
                latency_ms=round(latency_ms, 2),
                latency_seconds=round(latency_seconds, 3),
                thread_count=len(thread_history),
                semantic_count=len(semantic_results),
                total_tokens=total_tokens_used,
                adaptive_k=k,
                performance_target_met=latency_seconds < self.TARGET_LATENCY_SECONDS
            )

            # Assert performance target (AC #11: <3 seconds per NFR001)
            if latency_seconds >= self.TARGET_LATENCY_SECONDS:
                self.logger.warning(
                    "performance_target_missed",
                    email_id=email_id,
                    latency_seconds=round(latency_seconds, 3),
                    target_seconds=self.TARGET_LATENCY_SECONDS,
                    overage_seconds=round(latency_seconds - self.TARGET_LATENCY_SECONDS, 3)
                )

            return context

        except ValueError as e:
            # Email not found - re-raise for caller to handle
            self.logger.error(
                "context_retrieval_failed_email_not_found",
                email_id=email_id,
                user_id=self.user_id,
                error=str(e)
            )
            raise

        except Exception as e:
            # Log comprehensive error context
            latency_seconds = time.perf_counter() - start_time
            self.logger.error(
                "context_retrieval_failed",
                email_id=email_id,
                user_id=self.user_id,
                error=str(e),
                error_type=type(e).__name__,
                latency_seconds=round(latency_seconds, 3)
            )
            raise
