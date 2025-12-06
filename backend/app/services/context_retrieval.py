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
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import structlog
import tiktoken
from sqlmodel import select

from app.core.embedding_service import EmbeddingService
from app.core.gmail_client import GmailClient
from app.core.vector_db import VectorDBClient
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

    def __init__(
        self,
        user_id: int,
        db_service: DatabaseService = None,
        gmail_client: GmailClient = None,
        embedding_service: EmbeddingService = None,
        vector_db_client: VectorDBClient = None,
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
        # Use ChromaDB persist directory from settings
        from app.core.config import settings
        self.vector_db_client = vector_db_client or VectorDBClient(
            persist_directory=settings.CHROMADB_PATH
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

    async def _get_semantic_results(
        self,
        email_body: str,
        sender: str,
        k: int,
        user_id: int,
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

            # Query ChromaDB for top k most similar emails
            # Filter by user_id AND sender for conversation-specific context
            # ChromaDB requires $and operator for multiple filter conditions
            results = self.vector_db_client.query_embeddings(
                collection_name="email_embeddings",
                query_embedding=query_embedding,
                n_results=k,
                filter={
                    "$and": [
                        {"user_id": str(user_id)},  # Multi-tenant isolation
                        {"sender": sender}  # Conversation-specific context (same correspondent)
                    ]
                }
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

                    # Create EmailMessage with full body and metadata from ChromaDB
                    email_message: EmailMessage = {
                        "message_id": message_id,
                        "sender": email_detail["sender"],
                        "subject": email_detail["subject"],
                        "body": email_detail["body"],
                        "date": date_str,
                        "thread_id": email_detail["thread_id"]
                    }

                    # Store distance (cosine similarity) for ranking (will be used in _rank_semantic_results)
                    # Attach as temporary attribute for ranking, will be removed after ranking
                    email_message["_distance"] = distances[i]  # type: ignore

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

    def _rank_semantic_results(self, results: List[EmailMessage]) -> List[EmailMessage]:
        """Rank semantic results by relevance score and recency.

        Implements AC #7: Semantic results ranked by relevance score (cosine similarity)
        and recency (prefer recent emails if tie).

        Ranking algorithm:
        1. Primary sort: Cosine similarity score (descending, lower distance = higher similarity)
        2. Tiebreaker: Date (descending, prefer recent if scores within 0.01)

        Args:
            results: List of EmailMessage dicts with temporary _distance attribute

        Returns:
            List of EmailMessage dicts (ranked by relevance, then recency, _distance removed)

        Example:
            ranked_emails = service._rank_semantic_results(semantic_results)
        """
        if not results:
            return []

        # Sort by distance (ascending, lower = more similar) and date (descending, recent first)
        # Use stable sort to preserve order when scores are equal
        ranked_results = sorted(
            results,
            key=lambda email: (
                email.get("_distance", float("inf")),  # Primary: similarity score (lower = better)
                -self._parse_date_for_sort(email["date"])  # Secondary: recency (negative for descending)
            )
        )

        # Extract score and date ranges for logging
        distances = [email.get("_distance", 0.0) for email in ranked_results if "_distance" in email]
        dates = [email["date"] for email in ranked_results]

        score_range = {
            "min": min(distances) if distances else None,
            "max": max(distances) if distances else None
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

        # Remove temporary _distance attribute before returning
        for email in ranked_results:
            if "_distance" in email:
                del email["_distance"]  # type: ignore

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

            # Build contextual query for semantic search
            # Format: "From [sender] about [subject]: [body preview]"
            # This creates richer embeddings that capture conversation continuity
            email_query = f"From {sender_name} about {email_subject}: {full_body[:500]}"

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

            # Step 3: Calculate adaptive k based on thread length (AC #5)
            # DESIGN DECISION: Sequential execution required here to satisfy AC #5
            # Adaptive k logic DEPENDS on thread_length from Step 2, preventing parallelization
            # with semantic search (which requires k value). Parallel execution would require
            # fixed k, violating AC #5 requirement for dynamic k based on thread length.
            k = self._calculate_adaptive_k(original_thread_length)

            # Step 4: Perform semantic search if k > 0 (AC #3, #4)
            if k > 0:
                semantic_results = await self._get_semantic_results(
                    email_body=email_query,  # Use enhanced query instead of just subject
                    sender=email.sender,  # Filter by sender for conversation context
                    k=k,
                    user_id=self.user_id,
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
                "semantic_results": semantic_results,
                "metadata": {
                    "thread_length": original_thread_length,
                    "semantic_count": len(semantic_results),
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
