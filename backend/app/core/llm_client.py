"""Google Gemini LLM Client for Mail Agent.

This module provides a high-level wrapper for the Google Gemini API,
supporting text and JSON mode responses with automatic retry logic,
error handling, and token usage tracking.

Gemini 2.5 Flash Configuration:
- Model: gemini-2.5-flash
- Rate Limit: 1,000,000 tokens/minute (free tier)
- Cost: Free tier unlimited
- Retry Strategy: Exponential backoff (2s, 4s, 8s) for transient errors

Usage:
    client = LLMClient()

    # Text response
    response = client.send_prompt("Classify this email...")

    # JSON response
    result = client.receive_completion("Classify email: {content}")
    # Returns: {"suggested_folder": "Government", "reasoning": "..."}

Reference: https://ai.google.dev/gemini-api/docs/quickstart?lang=python
"""

import json
import os
import time
from typing import Dict, Optional

import google.generativeai as genai
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.core.metrics import gemini_token_usage_total
from app.utils.errors import (
    GeminiAPIError,
    GeminiInvalidRequestError,
    GeminiRateLimitError,
    GeminiTimeoutError,
)


class LLMClient:
    """Gemini API client wrapper with error handling and token tracking.

    Provides high-level methods for Gemini operations:
    - send_prompt(): Send prompt with text or JSON response format
    - receive_completion(): Wrapper for JSON-formatted responses
    - get_token_usage_stats(): Get cumulative token usage for monitoring

    Features:
    - Automatic retry with exponential backoff for rate limits and timeouts
    - JSON mode for structured output with schema validation
    - Token usage tracking with Prometheus metrics and structured logging
    - Custom exception handling for different error types
    """

    def __init__(self, api_key: str = None, model_name: str = None):
        """Initialize Gemini LLM client.

        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
            model_name: Model identifier (defaults to GEMINI_MODEL env var or gemini-2.5-flash)

        Raises:
            GeminiInvalidRequestError: If API key is missing or invalid
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise GeminiInvalidRequestError(
                "GEMINI_API_KEY environment variable not set. "
                "Get your API key from: https://makersuite.google.com/app/apikey"
            )

        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.logger = structlog.get_logger(__name__)

        # Configure Gemini SDK
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

        # Token usage tracking
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0

        self.logger.info(
            "llm_client_initialized",
            model_name=self.model_name,
            api_configured=True,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((GeminiRateLimitError, GeminiTimeoutError)),
        reraise=True,
    )
    def send_prompt(self, prompt: str, response_format: str = "text", operation: str = "general") -> str:
        """Send prompt to Gemini and return response.

        This method automatically retries on transient errors (rate limits, timeouts)
        with exponential backoff. Permanent errors (invalid requests) are not retried.

        Args:
            prompt: The prompt text to send to Gemini
            response_format: Response format - "text" (default) or "json" for structured output
            operation: Operation label for metrics (e.g., "classification", "response_generation")

        Returns:
            Response text from Gemini (plain text or JSON string)

        Raises:
            GeminiRateLimitError: Rate limit exceeded (429) - retried automatically
            GeminiTimeoutError: Request timeout - retried automatically
            GeminiInvalidRequestError: Invalid request (400, 403) - NOT retried
            GeminiAPIError: Other API errors

        Example:
            # Text mode
            response = client.send_prompt("Explain quantum computing")

            # JSON mode
            json_response = client.send_prompt(
                "Classify email: From tax@gov.de Subject: Tax deadline",
                response_format="json"
            )
        """
        start_time = time.time()
        prompt_preview = prompt[:100] + "..." if len(prompt) > 100 else prompt

        try:
            # Configure generation parameters
            generation_config = None
            if response_format == "json":
                generation_config = genai.GenerationConfig(
                    response_mime_type="application/json",
                )

            # Call Gemini API
            self.logger.info(
                "llm_call_started",
                model=self.model_name,
                prompt_length=len(prompt),
                response_format=response_format,
                operation=operation,
            )

            response = self.model.generate_content(prompt, generation_config=generation_config)

            # Extract response text
            response_text = response.text
            latency_ms = int((time.time() - start_time) * 1000)

            # Track token usage
            if hasattr(response, "usage_metadata"):
                prompt_tokens = response.usage_metadata.prompt_token_count
                completion_tokens = response.usage_metadata.candidates_token_count
                total_tokens = prompt_tokens + completion_tokens

                # Update cumulative counters
                self._total_prompt_tokens += prompt_tokens
                self._total_completion_tokens += completion_tokens

                # Update Prometheus metrics (separate counters for prompt and completion)
                gemini_token_usage_total.labels(token_type="prompt", model=self.model_name).inc(prompt_tokens)
                gemini_token_usage_total.labels(token_type="completion", model=self.model_name).inc(
                    completion_tokens
                )

                # Structured logging
                self.logger.info(
                    "llm_call_completed",
                    model=self.model_name,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    latency_ms=latency_ms,
                    response_length=len(response_text),
                    operation=operation,
                )
            else:
                self.logger.warning(
                    "llm_call_completed_no_usage_metadata",
                    model=self.model_name,
                    latency_ms=latency_ms,
                    response_length=len(response_text),
                )

            return response_text

        except genai.types.generation_types.BlockedPromptException as e:
            # Blocked prompt (inappropriate content) - permanent error, no retry
            self.logger.error(
                "llm_call_blocked_prompt",
                model=self.model_name,
                prompt_preview=prompt_preview,
                error=str(e),
            )
            raise GeminiInvalidRequestError(
                f"Prompt blocked by Gemini safety filters: {str(e)}", prompt_preview=prompt_preview
            )

        except genai.types.generation_types.StopCandidateException as e:
            # Generation stopped (safety or other reasons) - log and raise as invalid request
            self.logger.error(
                "llm_call_stopped",
                model=self.model_name,
                prompt_preview=prompt_preview,
                error=str(e),
            )
            raise GeminiInvalidRequestError(f"Gemini generation stopped: {str(e)}", prompt_preview=prompt_preview)

        except Exception as e:
            error_message = str(e).lower()

            # Rate limit error (429) - transient, will retry
            if "429" in error_message or "rate limit" in error_message or "quota" in error_message:
                self.logger.warning(
                    "llm_call_rate_limit",
                    model=self.model_name,
                    prompt_preview=prompt_preview,
                    error=str(e),
                )
                raise GeminiRateLimitError(f"Gemini rate limit exceeded: {str(e)}")

            # Timeout error - transient, will retry
            if "timeout" in error_message or "timed out" in error_message:
                self.logger.warning(
                    "llm_call_timeout",
                    model=self.model_name,
                    prompt_preview=prompt_preview,
                    error=str(e),
                )
                raise GeminiTimeoutError(f"Gemini request timeout: {str(e)}")

            # API key error (403) - permanent error, no retry
            if "403" in error_message or "api key" in error_message or "forbidden" in error_message:
                self.logger.error(
                    "llm_call_invalid_api_key",
                    model=self.model_name,
                    error=str(e),
                )
                raise GeminiInvalidRequestError(
                    f"Invalid Gemini API key. Check your GEMINI_API_KEY: {str(e)}"
                )

            # Generic API error
            self.logger.error(
                "llm_call_error",
                model=self.model_name,
                prompt_preview=prompt_preview,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise GeminiAPIError(f"Gemini API error: {str(e)}")

    def receive_completion(self, prompt: str, operation: str = "general") -> Dict:
        """Send prompt to Gemini and return parsed JSON response.

        This is a convenience wrapper around send_prompt() for JSON-formatted responses.
        Automatically parses the JSON response and validates it.

        Args:
            prompt: The prompt text to send to Gemini
            operation: Operation label for metrics (e.g., "classification")

        Returns:
            Parsed JSON response as dictionary

        Raises:
            GeminiInvalidRequestError: If response is not valid JSON
            GeminiRateLimitError: Rate limit exceeded (retried automatically)
            GeminiTimeoutError: Request timeout (retried automatically)
            GeminiAPIError: Other API errors

        Example:
            result = client.receive_completion(
                "Classify email: From tax@gov.de Subject: Tax deadline"
            )
            # Returns: {"suggested_folder": "Government", "reasoning": "..."}
        """
        response_text = self.send_prompt(prompt, response_format="json", operation=operation)

        try:
            parsed_json = json.loads(response_text)
            return parsed_json
        except json.JSONDecodeError as e:
            self.logger.error(
                "llm_json_parse_error",
                model=self.model_name,
                response_preview=response_text[:200],
                error=str(e),
            )
            raise GeminiInvalidRequestError(
                f"Failed to parse Gemini JSON response: {str(e)}", prompt_preview=response_text[:100]
            )

    def get_token_usage_stats(self) -> Dict[str, int]:
        """Get cumulative token usage statistics.

        Returns:
            Dictionary with token usage counts:
            - prompt_tokens: Total prompt tokens used
            - completion_tokens: Total completion tokens used
            - total_tokens: Sum of prompt and completion tokens

        Example:
            stats = client.get_token_usage_stats()
            print(f"Total tokens used: {stats['total_tokens']}")
            # Check if approaching free tier limit (1M tokens/minute)
            if stats['total_tokens'] > 900000:
                print("Warning: Approaching Gemini free tier limit")
        """
        return {
            "prompt_tokens": self._total_prompt_tokens,
            "completion_tokens": self._total_completion_tokens,
            "total_tokens": self._total_prompt_tokens + self._total_completion_tokens,
        }
