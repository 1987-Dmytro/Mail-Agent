"""Unit tests for EmbeddingService module.

Tests cover AC #1, #2, #4, #5, #6, #7, #9: Gemini text-embedding-004 model integration,
EmbeddingService class, single/batch embedding generation, dimension validation,
error handling, and API usage logging.

Test Functions:
1. test_embedding_service_initialization() - Verify initialization (AC #1, #2)
2. test_embed_text_returns_768_dimensions() - Verify single embedding (AC #4, #6)
3. test_embed_batch_processes_multiple_texts() - Verify batch processing (AC #5)
4. test_embedding_service_handles_api_errors() - Verify error handling (AC #7)
5. test_validate_dimensions_detects_invalid_output() - Verify dimension validation (AC #6)
6. test_api_usage_logging_records_requests() - Verify usage logging (AC #9)
"""

import os
from unittest.mock import Mock, patch, MagicMock

import pytest

from app.core.embedding_service import EmbeddingService
from app.utils.errors import (
    GeminiAPIError,
    GeminiInvalidRequestError,
    GeminiRateLimitError,
    GeminiTimeoutError,
)


class TestEmbeddingServiceInitialization:
    """Test suite for EmbeddingService initialization.

    Acceptance Criteria: AC #1, #2 - Gemini text-embedding-004 model integrated,
    EmbeddingService class created with configuration management
    """

    def test_embedding_service_initialization(self):
        """Verify EmbeddingService initializes correctly with API key (AC #1, #2).

        Test cases:
        - Successful init with env var
        - Explicit API key parameter
        - Missing API key raises error
        - Model name configuration
        """
        # Mock environment variable
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key"}):
            with patch("app.core.embedding_service.genai.configure") as mock_configure:
                service = EmbeddingService()

                # Verify initialization
                assert service.api_key == "test-api-key"
                assert service.model_name == "models/text-embedding-004"
                assert service.EXPECTED_DIMENSIONS == 768
                assert service.DEFAULT_BATCH_SIZE == 50

                # Verify genai.configure called with API key
                mock_configure.assert_called_once_with(api_key="test-api-key")

                # Verify usage tracking initialized
                assert service._total_requests == 0
                assert service._total_embeddings_generated == 0
                assert service._total_latency_ms == 0.0

    def test_embedding_service_explicit_api_key(self):
        """Verify EmbeddingService accepts explicit API key parameter (AC #2)."""
        with patch("app.core.embedding_service.genai.configure"):
            service = EmbeddingService(api_key="explicit-key")
            assert service.api_key == "explicit-key"

    def test_embedding_service_missing_api_key(self):
        """Verify EmbeddingService raises error when API key missing (AC #2)."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(GeminiInvalidRequestError, match="GEMINI_API_KEY"):
                EmbeddingService()

    def test_embedding_service_custom_model(self):
        """Verify EmbeddingService accepts custom model parameter (AC #1)."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("app.core.embedding_service.genai.configure"):
                service = EmbeddingService(model="custom-model")
                assert service.model_name == "models/custom-model"


class TestEmbedText:
    """Test suite for embed_text() method.

    Acceptance Criteria: AC #4, #6 - Single embedding generation (768-dim),
    dimension validation
    """

    def test_embed_text_returns_768_dimensions(self):
        """Verify embed_text() returns exactly 768-dimensional vector (AC #4, #6).

        Test cases:
        - Valid input returns 768-dim embedding
        - Embedding type is List[float]
        - Dimension validation passes
        """
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("app.core.embedding_service.genai.configure"):
                service = EmbeddingService()

                # Mock Gemini API response
                mock_embedding = [0.1] * 768
                mock_result = {"embedding": mock_embedding}

                with patch("app.core.embedding_service.genai.embed_content", return_value=mock_result):
                    embedding = service.embed_text("Test email content")

                    # Verify embedding dimensions
                    assert len(embedding) == 768
                    assert isinstance(embedding, list)
                    assert all(isinstance(x, (int, float)) for x in embedding)

                    # Verify dimension validation passes
                    assert service.validate_dimensions(embedding) is True

                    # Verify usage tracking updated
                    assert service._total_requests == 1
                    assert service._total_embeddings_generated == 1

    def test_embed_text_preprocesses_input(self):
        """Verify embed_text() preprocesses text before embedding (AC #4)."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("app.core.embedding_service.genai.configure"):
                service = EmbeddingService()

                mock_embedding = [0.1] * 768
                mock_result = {"embedding": mock_embedding}

                with patch("app.core.embedding_service.genai.embed_content", return_value=mock_result) as mock_embed:
                    # HTML input should be stripped
                    service.embed_text("<p>Email content</p>")

                    # Verify embed_content called with preprocessed text
                    call_args = mock_embed.call_args
                    assert "<" not in call_args.kwargs["content"]
                    assert "Email content" in call_args.kwargs["content"]

    def test_embed_text_raises_on_empty_input(self):
        """Verify embed_text() raises ValueError on empty input (AC #4)."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("app.core.embedding_service.genai.configure"):
                service = EmbeddingService()

                with pytest.raises(ValueError, match="cannot be empty"):
                    service.embed_text("")

                with pytest.raises(ValueError, match="cannot be empty"):
                    service.embed_text("   ")


class TestEmbedBatch:
    """Test suite for embed_batch() method.

    Acceptance Criteria: AC #5 - Batch embedding method processes up to 50 emails efficiently
    """

    def test_embed_batch_processes_multiple_texts(self):
        """Verify embed_batch() processes list of texts efficiently (AC #5).

        Test cases:
        - Batch of 10 texts processed successfully
        - All embeddings returned with 768 dimensions
        - batch_size parameter respected (max 50)
        """
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("app.core.embedding_service.genai.configure"):
                service = EmbeddingService()

                # Mock Gemini API response (one embedding per text)
                mock_embedding = [0.1] * 768
                mock_result = {"embedding": mock_embedding}

                texts = ["Email 1", "Email 2", "Email 3", "Email 4", "Email 5"]

                with patch("app.core.embedding_service.genai.embed_content", return_value=mock_result) as mock_embed:
                    embeddings = service.embed_batch(texts, batch_size=50)

                    # Verify all embeddings returned
                    assert len(embeddings) == len(texts)
                    assert all(len(emb) == 768 for emb in embeddings)

                    # Verify embed_content called for each text
                    assert mock_embed.call_count == len(texts)

                    # Verify usage tracking updated
                    assert service._total_requests == 1
                    assert service._total_embeddings_generated == len(texts)

    def test_embed_batch_respects_batch_size_limit(self):
        """Verify embed_batch() validates batch_size parameter (AC #5)."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("app.core.embedding_service.genai.configure"):
                service = EmbeddingService()

                # Invalid batch_size
                with pytest.raises(ValueError, match="batch_size must be between"):
                    service.embed_batch(["Email 1"], batch_size=0)

                with pytest.raises(ValueError, match="batch_size must be between"):
                    service.embed_batch(["Email 1"], batch_size=101)

    def test_embed_batch_raises_on_empty_list(self):
        """Verify embed_batch() raises ValueError on empty list (AC #5)."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("app.core.embedding_service.genai.configure"):
                service = EmbeddingService()

                with pytest.raises(ValueError, match="cannot be empty"):
                    service.embed_batch([])


class TestErrorHandling:
    """Test suite for API error handling.

    Acceptance Criteria: AC #7 - Error handling for API failures (rate limits,
    timeouts, invalid input) with retries
    """

    def test_embedding_service_handles_api_errors(self):
        """Verify error handling for API failures (AC #7).

        Test cases:
        - Rate limit errors (GeminiRateLimitError)
        - Timeout errors (GeminiTimeoutError)
        - Invalid request errors (GeminiInvalidRequestError)
        - Retry logic (3 attempts with exponential backoff)
        """
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("app.core.embedding_service.genai.configure"):
                service = EmbeddingService()

                # Test rate limit error
                with patch("app.core.embedding_service.genai.embed_content") as mock_embed:
                    mock_embed.side_effect = Exception("429 Rate limit exceeded")

                    with pytest.raises(GeminiRateLimitError, match="Rate limit exceeded"):
                        service.embed_text("Test text")

                # Test timeout error
                with patch("app.core.embedding_service.genai.embed_content") as mock_embed:
                    mock_embed.side_effect = Exception("Request timeout")

                    with pytest.raises(GeminiTimeoutError, match="timeout"):
                        service.embed_text("Test text")

                # Test invalid request error
                with patch("app.core.embedding_service.genai.embed_content") as mock_embed:
                    mock_embed.side_effect = Exception("400 Invalid request")

                    with pytest.raises(GeminiInvalidRequestError, match="Invalid request"):
                        service.embed_text("Test text")

    @patch("app.core.embedding_service.genai.embed_content")
    def test_retry_logic_with_exponential_backoff(self, mock_embed):
        """Verify retry logic attempts 3 times for transient errors (AC #7)."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("app.core.embedding_service.genai.configure"):
                service = EmbeddingService()

                # Simulate rate limit error on all attempts
                mock_embed.side_effect = Exception("429 Rate limit exceeded")

                with pytest.raises(GeminiRateLimitError):
                    service.embed_text("Test text")

                # Verify retry attempted 3 times (tenacity default)
                assert mock_embed.call_count == 3


class TestValidateDimensions:
    """Test suite for validate_dimensions() method.

    Acceptance Criteria: AC #6 - Embedding dimension validation (768-dim output)
    """

    def test_validate_dimensions_detects_invalid_output(self):
        """Verify validate_dimensions() detects non-768-dim vectors (AC #6).

        Test cases:
        - Valid 768-dim vector returns True
        - Invalid dimensions (767, 769, empty) return False
        """
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("app.core.embedding_service.genai.configure"):
                service = EmbeddingService()

                # Valid dimensions
                assert service.validate_dimensions([0.1] * 768) is True

                # Invalid dimensions
                assert service.validate_dimensions([0.1] * 767) is False
                assert service.validate_dimensions([0.1] * 769) is False
                assert service.validate_dimensions([]) is False
                assert service.validate_dimensions([0.1] * 100) is False


class TestAPIUsageLogging:
    """Test suite for API usage logging.

    Acceptance Criteria: AC #9 - API usage logging (track requests, tokens, latency)
    """

    def test_api_usage_logging_records_requests(self):
        """Verify API usage logging captures request metadata (AC #9).

        Test cases:
        - Requests counted correctly
        - Embeddings generated tracked
        - Latency measured and averaged
        - get_usage_stats() returns correct values
        """
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("app.core.embedding_service.genai.configure"):
                service = EmbeddingService()

                mock_embedding = [0.1] * 768
                mock_result = {"embedding": mock_embedding}

                # Generate single embedding
                with patch("app.core.embedding_service.genai.embed_content", return_value=mock_result):
                    service.embed_text("Test email 1")

                    # Check stats after first request
                    stats = service.get_usage_stats()
                    assert stats["total_requests"] == 1
                    assert stats["total_embeddings_generated"] == 1
                    assert stats["avg_latency_ms"] > 0

                # Generate batch embeddings
                with patch("app.core.embedding_service.genai.embed_content", return_value=mock_result):
                    service.embed_batch(["Email 1", "Email 2", "Email 3"])

                    # Check stats after batch request
                    stats = service.get_usage_stats()
                    assert stats["total_requests"] == 2  # 1 single + 1 batch
                    assert stats["total_embeddings_generated"] == 4  # 1 + 3
                    assert stats["avg_latency_ms"] > 0

    def test_get_usage_stats_returns_correct_format(self):
        """Verify get_usage_stats() returns dict with required fields (AC #9)."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("app.core.embedding_service.genai.configure"):
                service = EmbeddingService()

                stats = service.get_usage_stats()

                # Verify stats format
                assert isinstance(stats, dict)
                assert "total_requests" in stats
                assert "total_embeddings_generated" in stats
                assert "avg_latency_ms" in stats

                # Initial stats should be zero
                assert stats["total_requests"] == 0
                assert stats["total_embeddings_generated"] == 0
                assert stats["avg_latency_ms"] == 0.0


# Pytest fixtures
@pytest.fixture
def mock_embedding_service():
    """Create mocked EmbeddingService for testing."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
        with patch("app.core.embedding_service.genai.configure"):
            return EmbeddingService()


@pytest.fixture
def mock_768_embedding():
    """Create mock 768-dimensional embedding."""
    return [0.1] * 768


# Integration-style tests with fixtures
class TestEmbeddingServiceIntegration:
    """Integration tests for EmbeddingService complete workflows."""

    def test_complete_embedding_workflow(self, mock_embedding_service, mock_768_embedding):
        """Test complete embedding workflow: single + batch + stats (AC #4, #5, #9)."""
        service = mock_embedding_service
        mock_result = {"embedding": mock_768_embedding}

        with patch("app.core.embedding_service.genai.embed_content", return_value=mock_result):
            # Generate single embedding
            embedding1 = service.embed_text("Email content 1")
            assert len(embedding1) == 768

            # Generate batch embeddings
            batch_emails = ["Email 2", "Email 3", "Email 4"]
            embeddings_batch = service.embed_batch(batch_emails)
            assert len(embeddings_batch) == 3
            assert all(len(emb) == 768 for emb in embeddings_batch)

            # Check usage stats
            stats = service.get_usage_stats()
            assert stats["total_requests"] == 2
            assert stats["total_embeddings_generated"] == 4
