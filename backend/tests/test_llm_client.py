"""Unit tests for LLMClient (Gemini API wrapper).

Tests cover:
- Client initialization with environment variables
- Text and JSON mode prompt responses
- Error handling: rate limits, timeouts, invalid requests, blocked prompts
- Token usage tracking with Prometheus metrics
- Exponential backoff retry logic
- Structured logging validation
"""

import json
import os
from unittest.mock import MagicMock, Mock, patch

import pytest
import google.generativeai as genai

from app.core.llm_client import LLMClient
from app.utils.errors import (
    GeminiAPIError,
    GeminiInvalidRequestError,
    GeminiRateLimitError,
    GeminiTimeoutError,
)


# Test Fixtures
@pytest.fixture
def mock_env_vars():
    """Mock environment variables for Gemini configuration."""
    with patch.dict(
        os.environ,
        {
            "GEMINI_API_KEY": "test-api-key-12345",
            "GEMINI_MODEL": "gemini-2.5-flash",
        },
    ):
        yield


@pytest.fixture
def mock_genai_configure():
    """Mock genai.configure to prevent actual API calls during tests."""
    with patch("google.generativeai.configure") as mock_configure:
        yield mock_configure


@pytest.fixture
def mock_genai_model():
    """Mock GenerativeModel class."""
    with patch("google.generativeai.GenerativeModel") as mock_model_class:
        mock_model_instance = Mock()
        mock_model_class.return_value = mock_model_instance
        yield mock_model_instance


@pytest.fixture
def llm_client(mock_env_vars, mock_genai_configure, mock_genai_model):
    """LLMClient instance with mocked Gemini SDK."""
    return LLMClient()


@pytest.fixture
def sample_gemini_response():
    """Sample Gemini API response with token usage metadata."""
    mock_response = Mock()
    mock_response.text = "This is a sample response from Gemini."
    mock_response.usage_metadata = Mock()
    mock_response.usage_metadata.prompt_token_count = 15
    mock_response.usage_metadata.candidates_token_count = 10
    return mock_response


@pytest.fixture
def sample_json_response():
    """Sample Gemini JSON mode response."""
    json_data = {
        "suggested_folder": "Government",
        "reasoning": "Email from tax office regarding deadline",
        "priority_score": 85,
        "confidence": 0.92,
    }
    mock_response = Mock()
    mock_response.text = json.dumps(json_data)
    mock_response.usage_metadata = Mock()
    mock_response.usage_metadata.prompt_token_count = 20
    mock_response.usage_metadata.candidates_token_count = 30
    return mock_response


# Unit Tests
class TestLLMClientInitialization:
    """Tests for LLMClient initialization and configuration."""

    def test_initialization_with_env_vars(self, mock_env_vars, mock_genai_configure, mock_genai_model):
        """Test client initializes correctly with environment variables."""
        client = LLMClient()

        # Verify genai.configure called with API key
        mock_genai_configure.assert_called_once_with(api_key="test-api-key-12345")

        # Verify model name set correctly
        assert client.model_name == "gemini-2.5-flash"
        assert client.api_key == "test-api-key-12345"

    def test_initialization_with_explicit_params(self, mock_genai_configure, mock_genai_model):
        """Test client initializes with explicit API key and model name."""
        client = LLMClient(api_key="custom-key", model_name="gemini-1.5-pro")

        mock_genai_configure.assert_called_once_with(api_key="custom-key")
        assert client.model_name == "gemini-1.5-pro"
        assert client.api_key == "custom-key"

    def test_initialization_without_api_key(self, mock_genai_configure):
        """Test client raises error when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(GeminiInvalidRequestError) as exc_info:
                with patch("google.generativeai.GenerativeModel"):
                    LLMClient()

            assert "GEMINI_API_KEY environment variable not set" in str(exc_info.value)

    def test_token_usage_counters_initialized(self, llm_client):
        """Test token usage counters start at zero."""
        stats = llm_client.get_token_usage_stats()
        assert stats["prompt_tokens"] == 0
        assert stats["completion_tokens"] == 0
        assert stats["total_tokens"] == 0


class TestSendPrompt:
    """Tests for send_prompt method with text and JSON modes."""

    def test_send_prompt_success_text_mode(self, llm_client, sample_gemini_response):
        """Test successful text mode prompt with token tracking."""
        llm_client.model.generate_content = Mock(return_value=sample_gemini_response)

        response = llm_client.send_prompt("Test prompt", response_format="text")

        # Verify response
        assert response == "This is a sample response from Gemini."

        # Verify token usage tracked
        stats = llm_client.get_token_usage_stats()
        assert stats["prompt_tokens"] == 15
        assert stats["completion_tokens"] == 10
        assert stats["total_tokens"] == 25

    def test_send_prompt_json_mode(self, llm_client, sample_json_response):
        """Test JSON mode with GenerationConfig and response parsing."""
        llm_client.model.generate_content = Mock(return_value=sample_json_response)

        response = llm_client.send_prompt("Classify email", response_format="json")

        # Verify JSON response returned as string
        parsed = json.loads(response)
        assert parsed["suggested_folder"] == "Government"
        assert parsed["reasoning"] == "Email from tax office regarding deadline"

        # Verify generation_config passed with JSON mime type
        call_args = llm_client.model.generate_content.call_args
        generation_config = call_args.kwargs.get("generation_config")
        assert generation_config is not None
        assert generation_config.response_mime_type == "application/json"

    def test_receive_completion_wrapper(self, llm_client, sample_json_response):
        """Test receive_completion wrapper parses JSON automatically."""
        llm_client.model.generate_content = Mock(return_value=sample_json_response)

        result = llm_client.receive_completion("Classify email")

        # Verify returns parsed dict, not string
        assert isinstance(result, dict)
        assert result["suggested_folder"] == "Government"
        assert result["confidence"] == 0.92

    def test_send_prompt_with_operation_label(self, llm_client, sample_gemini_response):
        """Test operation label used for metrics tracking."""
        llm_client.model.generate_content = Mock(return_value=sample_gemini_response)

        with patch("app.core.llm_client.gemini_token_usage_total") as mock_metric:
            llm_client.send_prompt("Test", operation="classification")

            # Verify metric incremented with operation label
            mock_metric.labels.assert_called_with(operation="classification")
            mock_metric.labels().inc.assert_called_once()


class TestErrorHandling:
    """Tests for error handling and retry logic."""

    def test_rate_limit_error_429(self, llm_client):
        """Test rate limit error raises GeminiRateLimitError and retries."""
        # Mock to fail with 429 error all 3 attempts
        mock_error_response = Exception("429 Rate Limit Exceeded")
        llm_client.model.generate_content = Mock(
            side_effect=[mock_error_response, mock_error_response, mock_error_response]
        )

        with pytest.raises(GeminiRateLimitError) as exc_info:
            llm_client.send_prompt("Test prompt")

        assert "rate limit exceeded" in str(exc_info.value).lower()
        # Verify retried 3 times
        assert llm_client.model.generate_content.call_count == 3

    def test_timeout_error(self, llm_client):
        """Test timeout error raises GeminiTimeoutError and retries."""
        mock_error = Exception("Request timed out after 30 seconds")
        llm_client.model.generate_content = Mock(side_effect=[mock_error, mock_error, mock_error])

        with pytest.raises(GeminiTimeoutError) as exc_info:
            llm_client.send_prompt("Test prompt")

        assert "timeout" in str(exc_info.value).lower()
        # Verify retried 3 times
        assert llm_client.model.generate_content.call_count == 3

    def test_blocked_prompt_error_no_retry(self, llm_client):
        """Test blocked prompt (inappropriate content) raises error without retry."""
        mock_error = genai.types.generation_types.BlockedPromptException("Prompt blocked by safety filters")
        llm_client.model.generate_content = Mock(side_effect=mock_error)

        with pytest.raises(GeminiInvalidRequestError) as exc_info:
            llm_client.send_prompt("Inappropriate content")

        assert "blocked" in str(exc_info.value).lower()
        # Verify only called once (no retry for permanent error)
        assert llm_client.model.generate_content.call_count == 1

    def test_invalid_api_key_error(self, llm_client):
        """Test invalid API key (403) raises GeminiInvalidRequestError."""
        mock_error = Exception("403 Forbidden: API key invalid")
        llm_client.model.generate_content = Mock(side_effect=mock_error)

        with pytest.raises(GeminiInvalidRequestError) as exc_info:
            llm_client.send_prompt("Test prompt")

        assert "api key" in str(exc_info.value).lower()

    def test_stop_candidate_exception(self, llm_client):
        """Test StopCandidateException handled as invalid request."""
        mock_error = genai.types.generation_types.StopCandidateException("Generation stopped due to safety")
        llm_client.model.generate_content = Mock(side_effect=mock_error)

        with pytest.raises(GeminiInvalidRequestError) as exc_info:
            llm_client.send_prompt("Test prompt")

        assert "stopped" in str(exc_info.value).lower()

    def test_generic_api_error(self, llm_client):
        """Test unknown API error raises GeminiAPIError."""
        mock_error = Exception("Unknown API error occurred")
        llm_client.model.generate_content = Mock(side_effect=mock_error)

        with pytest.raises(GeminiAPIError) as exc_info:
            llm_client.send_prompt("Test prompt")

        assert "Gemini API error" in str(exc_info.value)


class TestTokenUsageTracking:
    """Tests for token usage tracking and Prometheus metrics."""

    def test_token_usage_extracted_from_response(self, llm_client, sample_gemini_response):
        """Test token counts extracted from response metadata."""
        llm_client.model.generate_content = Mock(return_value=sample_gemini_response)

        llm_client.send_prompt("Test prompt")

        stats = llm_client.get_token_usage_stats()
        assert stats["prompt_tokens"] == 15
        assert stats["completion_tokens"] == 10
        assert stats["total_tokens"] == 25

    def test_token_usage_cumulative(self, llm_client, sample_gemini_response):
        """Test token usage accumulates across multiple calls."""
        llm_client.model.generate_content = Mock(return_value=sample_gemini_response)

        # Make multiple calls
        llm_client.send_prompt("First prompt")
        llm_client.send_prompt("Second prompt")
        llm_client.send_prompt("Third prompt")

        stats = llm_client.get_token_usage_stats()
        assert stats["prompt_tokens"] == 15 * 3  # 45
        assert stats["completion_tokens"] == 10 * 3  # 30
        assert stats["total_tokens"] == 25 * 3  # 75

    def test_prometheus_metric_incremented(self, llm_client, sample_gemini_response):
        """Test Prometheus counter incremented with token count."""
        llm_client.model.generate_content = Mock(return_value=sample_gemini_response)

        with patch("app.core.llm_client.gemini_token_usage_total") as mock_metric:
            llm_client.send_prompt("Test", operation="test_op")

            # Verify metric incremented by total_tokens (25)
            mock_metric.labels.assert_called_with(operation="test_op")
            mock_metric.labels().inc.assert_called_once_with(25)

    def test_no_usage_metadata_warning(self, llm_client):
        """Test warning logged when response has no usage metadata."""
        mock_response = Mock()
        mock_response.text = "Response without metadata"
        # Remove usage_metadata attribute
        del mock_response.usage_metadata

        llm_client.model.generate_content = Mock(return_value=mock_response)

        with patch.object(llm_client.logger, "warning") as mock_logger:
            llm_client.send_prompt("Test prompt")

            # Verify warning logged
            mock_logger.assert_called_once()
            call_args = mock_logger.call_args[0]
            assert "no_usage_metadata" in call_args[0]


class TestJSONParsing:
    """Tests for JSON response parsing and validation."""

    def test_receive_completion_parse_error(self, llm_client):
        """Test JSON parse error raises GeminiInvalidRequestError."""
        mock_response = Mock()
        mock_response.text = "This is not valid JSON"
        mock_response.usage_metadata = Mock()
        mock_response.usage_metadata.prompt_token_count = 5
        mock_response.usage_metadata.candidates_token_count = 5

        llm_client.model.generate_content = Mock(return_value=mock_response)

        with pytest.raises(GeminiInvalidRequestError) as exc_info:
            llm_client.receive_completion("Test prompt")

        assert "parse" in str(exc_info.value).lower()
        assert "json" in str(exc_info.value).lower()


class TestRetryLogic:
    """Tests for exponential backoff retry behavior."""

    def test_retry_on_rate_limit_then_success(self, llm_client, sample_gemini_response):
        """Test retry succeeds after rate limit error."""
        mock_error = Exception("429 rate limit exceeded")
        llm_client.model.generate_content = Mock(side_effect=[mock_error, sample_gemini_response])

        # Should succeed on second attempt
        response = llm_client.send_prompt("Test prompt")
        assert response == "This is a sample response from Gemini."

        # Verify called twice (1 fail + 1 success)
        assert llm_client.model.generate_content.call_count == 2

    def test_retry_exhausted_after_3_attempts(self, llm_client):
        """Test retry stops after 3 attempts for transient errors."""
        mock_error = Exception("timeout error")
        llm_client.model.generate_content = Mock(side_effect=mock_error)

        with pytest.raises(GeminiTimeoutError):
            llm_client.send_prompt("Test prompt")

        # Verify called 3 times (tenacity stop_after_attempt(3))
        assert llm_client.model.generate_content.call_count == 3

    def test_no_retry_on_permanent_error(self, llm_client):
        """Test permanent errors (blocked prompt) not retried."""
        mock_error = genai.types.generation_types.BlockedPromptException("Blocked")
        llm_client.model.generate_content = Mock(side_effect=mock_error)

        with pytest.raises(GeminiInvalidRequestError):
            llm_client.send_prompt("Test prompt")

        # Verify called only once (no retry for permanent error)
        assert llm_client.model.generate_content.call_count == 1
