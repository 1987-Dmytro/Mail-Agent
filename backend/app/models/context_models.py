"""
Context Retrieval Data Models

TypedDict structures for Smart Hybrid RAG context retrieval (Story 3.4).
These lightweight data structures are used to pass context between services
without the overhead of database models or validation.

Created: 2025-11-09
Epic: 3 (RAG System & Response Generation)
Story: 3.4 (Context Retrieval Service)
"""

from datetime import datetime
from typing import Any, Dict, List, TypedDict


class EmailMessage(TypedDict):
    """
    Represents a single email message in context retrieval.

    Used in both thread_history and semantic_results lists within RAGContext.
    Contains essential email metadata needed for AI response generation.

    Attributes:
        message_id: Gmail message ID (unique identifier)
        sender: Email sender address
        subject: Email subject line
        body: Full email body text (HTML stripped, plain text)
        date: Email timestamp (ISO 8601 format or datetime)
        thread_id: Gmail thread ID (for conversation grouping)

    Example:
        {
            "message_id": "18b7c8d9e0f1a2b3",
            "sender": "finanzamt@example.de",
            "subject": "Tax Return Deadline Reminder",
            "body": "Dear citizen, please submit your tax return by...",
            "date": "2025-11-09T14:30:00Z",
            "thread_id": "18b7c8d9e0f1a2b3"
        }
    """
    message_id: str
    sender: str
    subject: str
    body: str
    date: str  # ISO 8601 format timestamp
    thread_id: str


class RAGContext(TypedDict):
    """
    Smart Hybrid RAG context structure combining thread history and semantic search.

    This structure is returned by ContextRetrievalService.retrieve_context() and
    passed to the AI response generation service (Story 3.7). It combines:
    - Thread history: Last 5 emails in conversation for continuity
    - Semantic results: Top 3-7 similar emails for broader context
    - Metadata: Statistics about the context retrieval

    The token budget is enforced at ~6.5K tokens total (leaving 25K for response
    generation within Gemini's 32K context window).

    Attributes:
        thread_history: Last 5 emails in thread (chronological order, oldest → newest)
        sender_history: ALL emails from sender (last 90 days, chronological order)
        semantic_results: Top 3-7 similar emails (ranked by relevance score descending)
        metadata: Statistics and metadata about the context:
            - thread_length: Original thread length before truncation
            - semantic_count: Number of semantic results retrieved
            - sender_history_count: Number of emails in sender history
            - oldest_thread_date: Timestamp of oldest email in thread_history
            - total_tokens_used: Total token count of all email bodies in context

    Example:
        {
            "thread_history": [
                {"message_id": "123", "sender": "user@example.com", ...},
                {"message_id": "124", "sender": "finanzamt@example.de", ...}
            ],
            "semantic_results": [
                {"message_id": "456", "sender": "finanzamt@example.de", ...},
                {"message_id": "789", "sender": "finanzamt@example.de", ...}
            ],
            "metadata": {
                "thread_length": 4,
                "semantic_count": 3,
                "oldest_thread_date": "2025-10-15T10:00:00Z",
                "total_tokens_used": 5800
            }
        }
    """
    thread_history: List[EmailMessage]
    sender_history: List[EmailMessage]  # NEW: Full sender conversation history (90 days)
    semantic_results: List[EmailMessage]
    metadata: Dict[str, Any]  # Includes: thread_length, semantic_count, sender_history_count, oldest_thread_date, total_tokens_used
