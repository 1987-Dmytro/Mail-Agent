"""Google Gemini Embedding Service for Mail Agent.

This module provides a high-level wrapper for the Google Gemini Embedding API,
supporting single and batch embedding generation with automatic retry logic,
error handling, and usage tracking.

Gemini text-embedding-004 Configuration:
- Model: text-embedding-004
- Dimensions: 768
- Rate Limit: 50 requests/minute (safe limit)
- Cost: Free tier unlimited
- Multilingual: Supports 50+ languages including ru/uk/en/de
- Retry Strategy: Exponential backoff (2s, 4s, 8s) for transient errors

Usage:
    service = EmbeddingService()

    # Single embedding
    embedding = service.embed_text("Email content here...")
    # Returns: List[float] with 768 dimensions

    # Batch embedding
    embeddings = service.embed_batch(["Email 1", "Email 2", ...])
    # Returns: List[List[float]], each with 768 dimensions

Reference: https://ai.google.dev/gemini-api/docs/embeddings
"""

import os
import time
from typing import List, Optional

import google.generativeai as genai
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.core.preprocessing import (
    strip_html,
    extract_email_text,
    truncate_to_tokens,
)
from app.utils.errors import (
    GeminiAPIError,
    GeminiInvalidRequestError,
    GeminiRateLimitError,
    GeminiTimeoutError,
)


class EmbeddingService:
    """Gemini Embedding API client wrapper with error handling and usage tracking.

    Provides high-level methods for embedding operations:
    - embed_text(): Generate single embedding (768-dim)
    - embed_batch(): Generate batch embeddings (up to 50 per batch)
    - validate_dimensions(): Verify 768-dim output
    - get_usage_stats(): Get cumulative usage statistics

    Features:
    - Automatic retry with exponential backoff for rate limits and timeouts
    - Email preprocessing (HTML stripping, truncation to 2048 tokens)
    - 768-dimensional embeddings matching ChromaDB collection
    - Batch processing with rate limit awareness (50 requests/min)
    - Usage tracking with structured logging
    """

    # Expected embedding dimension for text-embedding-004
    EXPECTED_DIMENSIONS = 768

    # Recommended batch size for rate limiting (50 requests/min = safe limit)
    DEFAULT_BATCH_SIZE = 50

    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-004"):
        """Initialize Gemini Embedding service.

        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
            model: Embedding model identifier (default: text-embedding-004)

        Raises:
            GeminiInvalidRequestError: If API key is missing or invalid

        Example:
            # Default initialization (from env var)
            service = EmbeddingService()

            # Explicit API key
            service = EmbeddingService(api_key="your-api-key-here")
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise GeminiInvalidRequestError(
                "GEMINI_API_KEY environment variable not set. "
                "Get your API key from: https://makersuite.google.com/app/apikey"
            )

        self.model_name = f"models/{model}"
        self.logger = structlog.get_logger(__name__)

        # Configure Gemini SDK
        genai.configure(api_key=self.api_key)

        # Usage tracking
        self._total_requests = 0
        self._total_embeddings_generated = 0
        self._total_latency_ms = 0.0

        self.logger.info(
            "embedding_service_initialized",
            model_name=self.model_name,
            expected_dimensions=self.EXPECTED_DIMENSIONS,
            api_configured=True,
        )

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text before embedding generation.

        Applies preprocessing pipeline:
        1. Strip HTML tags (if present)
        2. Truncate to 2048 tokens max

        Args:
            text: Raw text to preprocess

        Returns:
            Preprocessed text ready for embedding

        Example:
            preprocessed = service._preprocess_text("<p>Email content</p>")
            # Returns: "Email content" (HTML stripped, truncated if needed)
        """
        # Strip HTML if present (detect by looking for tags)
        if "<" in text and ">" in text:
            text = strip_html(text)

        # Truncate to token limit
        text = truncate_to_tokens(text, max_tokens=2048)

        return text

    def _handle_api_error(self, error: Exception, operation: str) -> None:
        """Centralized error handling for Gemini API calls.

        Args:
            error: The exception that occurred
            operation: Operation name for logging (e.g., "embed_text", "embed_batch")

        Raises:
            GeminiRateLimitError: If rate limit exceeded (429)
            GeminiTimeoutError: If request timed out
            GeminiInvalidRequestError: If invalid request (400, 403)
            GeminiAPIError: For other API errors
        """
        error_msg = str(error)

        # Determine error type and raise appropriate exception
        if "429" in error_msg or "rate limit" in error_msg.lower():
            self.logger.warning(
                "gemini_rate_limit_exceeded",
                operation=operation,
                error=error_msg,
            )
            raise GeminiRateLimitError(f"Rate limit exceeded during {operation}: {error_msg}")

        elif "timeout" in error_msg.lower():
            self.logger.warning(
                "gemini_timeout",
                operation=operation,
                error=error_msg,
            )
            raise GeminiTimeoutError(f"Request timeout during {operation}: {error_msg}")

        elif "400" in error_msg or "403" in error_msg or "invalid" in error_msg.lower():
            self.logger.error(
                "gemini_invalid_request",
                operation=operation,
                error=error_msg,
            )
            raise GeminiInvalidRequestError(f"Invalid request during {operation}: {error_msg}")

        else:
            self.logger.error(
                "gemini_api_error",
                operation=operation,
                error=error_msg,
                error_type=type(error).__name__,
            )
            raise GeminiAPIError(f"API error during {operation}: {error_msg}")

    def validate_dimensions(self, embedding: List[float]) -> bool:
        """Validate that embedding has expected dimensions (768).

        Args:
            embedding: Embedding vector to validate

        Returns:
            True if embedding has exactly 768 dimensions, False otherwise

        Example:
            valid = service.validate_dimensions(embedding_vector)
            if not valid:
                raise ValueError("Invalid embedding dimensions")
        """
        is_valid = len(embedding) == self.EXPECTED_DIMENSIONS

        if not is_valid:
            self.logger.warning(
                "invalid_embedding_dimensions",
                expected=self.EXPECTED_DIMENSIONS,
                actual=len(embedding),
            )

        return is_valid

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((GeminiRateLimitError, GeminiTimeoutError)),
        reraise=True,
    )
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for single text string.

        This method automatically retries on transient errors (rate limits, timeouts)
        with exponential backoff. Text is preprocessed (HTML stripped, truncated)
        before embedding generation.

        Args:
            text: Text to embed (HTML will be stripped, truncated to 2048 tokens)

        Returns:
            768-dimensional embedding vector as List[float]

        Raises:
            GeminiRateLimitError: Rate limit exceeded (429) - retried automatically
            GeminiTimeoutError: Request timeout - retried automatically
            GeminiInvalidRequestError: Invalid request (400, 403) - NOT retried
            GeminiAPIError: Other API errors
            ValueError: If text is empty after preprocessing

        Example:
            embedding = service.embed_text("Email subject and body...")
            assert len(embedding) == 768
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        start_time = time.perf_counter()

        # Preprocess text
        preprocessed_text = self._preprocess_text(text)

        if not preprocessed_text:
            raise ValueError("Text is empty after preprocessing")

        try:
            # Call Gemini Embedding API
            self.logger.info(
                "embedding_started",
                text_length=len(preprocessed_text),
                model=self.model_name,
            )

            result = genai.embed_content(
                model=self.model_name,
                content=preprocessed_text,
                task_type="retrieval_document",  # For semantic search/retrieval
            )

            embedding = result["embedding"]

            # Validate dimensions
            if not self.validate_dimensions(embedding):
                raise GeminiAPIError(
                    f"Invalid embedding dimensions: expected {self.EXPECTED_DIMENSIONS}, "
                    f"got {len(embedding)}"
                )

            # Track metrics
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._total_requests += 1
            self._total_embeddings_generated += 1
            self._total_latency_ms += latency_ms

            self.logger.info(
                "embedding_completed",
                dimensions=len(embedding),
                latency_ms=round(latency_ms, 2),
                model=self.model_name,
            )

            return embedding

        except (GeminiRateLimitError, GeminiTimeoutError, GeminiInvalidRequestError, GeminiAPIError):
            # Re-raise known errors (already wrapped)
            raise

        except Exception as e:
            # Wrap unknown errors
            self._handle_api_error(e, operation="embed_text")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((GeminiRateLimitError, GeminiTimeoutError)),
        reraise=True,
    )
    def embed_batch(self, texts: List[str], batch_size: int = DEFAULT_BATCH_SIZE) -> List[List[float]]:
        """Generate embeddings for multiple texts efficiently.

        Processes texts in batches to respect rate limits (50 requests/min recommended).
        Each text is preprocessed before embedding generation.

        Args:
            texts: List of texts to embed
            batch_size: Maximum batch size (default: 50 for rate limiting)

        Returns:
            List of 768-dimensional embedding vectors (one per input text)

        Raises:
            GeminiRateLimitError: Rate limit exceeded - retried automatically
            GeminiTimeoutError: Request timeout - retried automatically
            GeminiInvalidRequestError: Invalid request - NOT retried
            GeminiAPIError: Other API errors
            ValueError: If texts list is empty or batch_size invalid

        Example:
            emails = ["Email 1 content", "Email 2 content", ...]
            embeddings = service.embed_batch(emails, batch_size=50)
            assert len(embeddings) == len(emails)
            assert all(len(emb) == 768 for emb in embeddings)
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        if batch_size <= 0 or batch_size > 100:
            raise ValueError(f"batch_size must be between 1 and 100, got {batch_size}")

        start_time = time.perf_counter()

        # Preprocess all texts
        preprocessed_texts = []
        for text in texts:
            if text and text.strip():
                preprocessed = self._preprocess_text(text)
                if preprocessed:
                    preprocessed_texts.append(preprocessed)
                else:
                    # Empty after preprocessing - use placeholder
                    preprocessed_texts.append("[empty]")
            else:
                # Empty input - use placeholder
                preprocessed_texts.append("[empty]")

        try:
            self.logger.info(
                "batch_embedding_started",
                batch_size=len(preprocessed_texts),
                model=self.model_name,
            )

            # Generate embeddings using BATCH API (much faster and avoids rate limits!)
            # Gemini API supports batch embedding - process all texts in single request
            result = genai.embed_content(
                model=self.model_name,
                content=preprocessed_texts,  # Pass entire list!
                task_type="retrieval_document",
            )

            # Extract embeddings from batch result
            embeddings = result["embedding"]

            # Validate all dimensions
            for i, embedding in enumerate(embeddings):
                if not self.validate_dimensions(embedding):
                    raise GeminiAPIError(
                        f"Invalid embedding dimensions at index {i}: "
                        f"expected {self.EXPECTED_DIMENSIONS}, got {len(embedding)}"
                    )

            # Track metrics
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._total_requests += 1
            self._total_embeddings_generated += len(embeddings)
            self._total_latency_ms += latency_ms

            self.logger.info(
                "batch_embedding_completed",
                batch_size=len(embeddings),
                latency_ms=round(latency_ms, 2),
                avg_latency_per_embedding_ms=round(latency_ms / len(embeddings), 2),
                model=self.model_name,
            )

            return embeddings

        except (GeminiRateLimitError, GeminiTimeoutError, GeminiInvalidRequestError, GeminiAPIError):
            # Re-raise known errors
            raise

        except Exception as e:
            # Wrap unknown errors
            self._handle_api_error(e, operation="embed_batch")

    def get_usage_stats(self) -> dict:
        """Get cumulative usage statistics for monitoring.

        Returns:
            Dictionary with usage stats:
            - total_requests: Total API requests made
            - total_embeddings_generated: Total embeddings generated
            - avg_latency_ms: Average latency per request in milliseconds

        Example:
            stats = service.get_usage_stats()
            print(f"Generated {stats['total_embeddings_generated']} embeddings")
            print(f"Average latency: {stats['avg_latency_ms']}ms")
        """
        avg_latency = (
            self._total_latency_ms / self._total_requests if self._total_requests > 0 else 0.0
        )

        stats = {
            "total_requests": self._total_requests,
            "total_embeddings_generated": self._total_embeddings_generated,
            "avg_latency_ms": round(avg_latency, 2),
        }

        self.logger.debug("usage_stats_retrieved", **stats)

        return stats
