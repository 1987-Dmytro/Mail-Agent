"""GROQ LLM Client for Mail Agent.

This module provides a high-level wrapper for the GROQ API,
supporting text and JSON mode responses with automatic retry logic,
error handling, and token usage tracking.

GROQ API Configuration:
- Models: llama-3.3-70b-versatile, openai/gpt-oss-120b, etc.
- Free Tier Rate Limits:
  - 30 RPM (requests per minute)
  - 1,000 RPD (requests per day)
  - 6,000 TPM (tokens per minute)
- Retry Strategy: Exponential backoff (2s, 4s, 8s) for transient errors

Usage:
    client = GroqLLMClient()

    # Text response
    response = client.send_prompt("Classify this email...")

    # JSON response
    result = client.receive_completion("Classify email: {content}")
    # Returns: {"suggested_folder": "Government", "reasoning": "..."}

Reference: https://console.groq.com/docs/quickstart
"""

import json
import os
from typing import Dict, Optional

import structlog
from groq import Groq
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.core.metrics import gemini_token_usage_total  # Reuse same metrics
from app.utils.errors import (
    GeminiAPIError,
    GeminiInvalidRequestError,
    GeminiRateLimitError,
    GeminiTimeoutError,
)


class GroqLLMClient:
    """GROQ API client wrapper with error handling and token tracking.

    Provides high-level methods for GROQ operations:
    - send_prompt(): Send prompt with text or JSON response format
    - receive_completion(): Wrapper for JSON-formatted responses
    - get_token_usage_stats(): Get cumulative token usage for monitoring

    Features:
    - Automatic retry with exponential backoff for rate limits and timeouts
    - JSON mode for structured output
    - Token usage tracking with Prometheus metrics and structured logging
    - Compatible interface with GeminiLLMClient for easy migration
    """

    def __init__(self, api_key: str = None, model_name: str = None):
        """Initialize GROQ LLM client.

        Args:
            api_key: GROQ API key (defaults to GROQ_API_KEY or LLM_API_KEY env var)
            model_name: Model identifier (defaults to GROQ_MODEL env var or llama-3.3-70b-versatile)

        Raises:
            GeminiInvalidRequestError: If API key is missing or invalid
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY")
        if not self.api_key:
            raise GeminiInvalidRequestError(
                "GROQ_API_KEY or LLM_API_KEY environment variable not set. "
                "Get your API key from: https://console.groq.com/keys"
            )

        self.model_name = model_name or os.getenv("GROQ_MODEL") or os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
        self.logger = structlog.get_logger(__name__)

        # Initialize GROQ client
        self.client = Groq(api_key=self.api_key)

        # Token usage tracking
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0

        self.logger.info(
            "groq_client_initialized",
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
        """Send prompt to GROQ and get response.

        Implements automatic retry with exponential backoff for rate limits and timeouts.
        Token usage is tracked and logged for monitoring.

        Args:
            prompt: User prompt text
            response_format: Response format - "text" or "json"
            operation: Operation name for logging (e.g., "classification", "general")

        Returns:
            Response text (raw text or JSON string)

        Raises:
            GeminiRateLimitError: If rate limit exceeded after retries
            GeminiTimeoutError: If request times out after retries
            GeminiInvalidRequestError: If prompt is invalid (e.g., safety filters)
            GeminiAPIError: For other API errors
        """
        try:
            self.logger.info(
                "llm_call_started",
                operation=operation,
                model=self.model_name,
                prompt_length=len(prompt),
                response_format=response_format,
            )

            # Prepare request parameters
            kwargs = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": float(os.getenv("DEFAULT_LLM_TEMPERATURE", "0.1")),
                "max_tokens": int(os.getenv("MAX_TOKENS", "2000")),
            }

            # Add JSON mode if requested
            if response_format == "json":
                kwargs["response_format"] = {"type": "json_object"}

            # Make API call
            response = self.client.chat.completions.create(**kwargs)

            # Extract response text
            response_text = response.choices[0].message.content

            # Track token usage
            if hasattr(response, "usage"):
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
                total_tokens = response.usage.total_tokens

                self._total_prompt_tokens += prompt_tokens
                self._total_completion_tokens += completion_tokens

                # Update Prometheus metrics (reuse gemini metrics)
                gemini_token_usage_total.labels(token_type="prompt", model=self.model_name).inc(prompt_tokens)
                gemini_token_usage_total.labels(token_type="completion", model=self.model_name).inc(
                    completion_tokens
                )

                self.logger.info(
                    "llm_call_success",
                    operation=operation,
                    model=self.model_name,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    response_length=len(response_text),
                )

            return response_text

        except Exception as e:
            error_message = str(e).lower()

            # Map GROQ errors to our custom exceptions
            if "rate" in error_message or "429" in error_message or "quota" in error_message:
                self.logger.warning("llm_call_rate_limit", operation=operation, error=str(e))
                raise GeminiRateLimitError(f"GROQ rate limit exceeded: {e}")

            elif "timeout" in error_message or "timed out" in error_message:
                self.logger.warning("llm_call_timeout", operation=operation, error=str(e))
                raise GeminiTimeoutError(f"GROQ request timeout: {e}")

            elif "invalid" in error_message or "400" in error_message:
                self.logger.error("llm_call_invalid_request", operation=operation, error=str(e))
                raise GeminiInvalidRequestError(f"Invalid GROQ request: {e}")

            else:
                self.logger.error(
                    "llm_call_error",
                    operation=operation,
                    error_type=type(e).__name__,
                    error=str(e),
                )
                raise GeminiAPIError(f"GROQ API error: {e}")

    def receive_completion(self, prompt: str, operation: str = "general") -> Dict:
        """Convenience wrapper for JSON-formatted responses.

        This method is a high-level wrapper that:
        1. Sends the prompt with JSON response format
        2. Parses the JSON response
        3. Returns the parsed dictionary

        Args:
            prompt: User prompt text
            operation: Operation name for logging

        Returns:
            Parsed JSON response as dictionary

        Raises:
            GeminiAPIError: If response is not valid JSON
            (plus all exceptions from send_prompt)
        """
        try:
            response_text = self.send_prompt(prompt, response_format="json", operation=operation)
            return json.loads(response_text)

        except json.JSONDecodeError as e:
            self.logger.error(
                "llm_json_parse_error",
                operation=operation,
                error=str(e),
                response_text=response_text[:200],  # Log first 200 chars
            )
            raise GeminiAPIError(f"Failed to parse GROQ JSON response: {e}")

    def get_token_usage_stats(self) -> Dict[str, int]:
        """Get cumulative token usage statistics.

        Returns:
            Dict with keys: prompt_tokens, completion_tokens, total_tokens
        """
        return {
            "prompt_tokens": self._total_prompt_tokens,
            "completion_tokens": self._total_completion_tokens,
            "total_tokens": self._total_prompt_tokens + self._total_completion_tokens,
        }
