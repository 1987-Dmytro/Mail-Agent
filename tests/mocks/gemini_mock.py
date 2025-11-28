"""Mock Gemini API client for integration testing.

This mock provides deterministic responses for testing email classification
without making real API calls to Google Gemini.
"""

from typing import Any, Dict, List


class MockGeminiClient:
    """Mock implementation of Gemini LLM client for testing.

    Tracks all method calls for test assertions and returns configurable
    deterministic responses based on email content patterns.
    """

    def __init__(self):
        """Initialize mock with empty call tracking."""
        self.calls: List[Dict[str, Any]] = []
        self._custom_responses: Dict[str, Dict[str, Any]] = {}
        self._response_delay: float = 0.0
        self._failure_exception: Exception | None = None
        self._failure_count: int = 0
        self._current_call_count: int = 0

    def set_custom_response(self, pattern: str, response: Dict[str, Any]):
        """Configure custom response for specific email patterns.

        Args:
            pattern: String pattern to match in prompt (case-insensitive)
            response: Classification response to return when pattern matches
        """
        self._custom_responses[pattern.lower()] = response

    def set_response_delay(self, delay: float):
        """Set artificial delay for API responses to simulate latency.

        Args:
            delay: Delay in seconds to add before returning responses
        """
        self._response_delay = delay

    def set_failure_mode(self, exception: Exception, fail_count: int):
        """Configure mock to raise exceptions for testing error handling.

        Args:
            exception: Exception to raise on API calls
            fail_count: Number of calls that should fail before succeeding
        """
        self._failure_exception = exception
        self._failure_count = fail_count
        self._current_call_count = 0

    async def classify_email(self, prompt: str) -> Dict[str, Any]:
        """Mock email classification that returns deterministic results.

        Args:
            prompt: Classification prompt containing email content

        Returns:
            dict: Classification response with suggested_folder, reasoning,
                  priority_score, and confidence
        """
        # Track call for assertions
        self.calls.append({
            "method": "classify_email",
            "prompt": prompt
        })

        # Handle failure mode
        self._current_call_count += 1
        if self._failure_exception and self._current_call_count <= self._failure_count:
            raise self._failure_exception

        # Add artificial delay if configured
        if self._response_delay > 0:
            import asyncio
            await asyncio.sleep(self._response_delay)

        # Check for custom responses first
        for pattern, response in self._custom_responses.items():
            if pattern in prompt.lower():
                return response

        # Deterministic responses based on content patterns
        if "finanzamt" in prompt.lower() or "tax" in prompt.lower():
            return {
                "suggested_folder": "Government",
                "reasoning": "Email from tax office regarding official tax documents",
                "priority_score": 85,
                "confidence": 0.92
            }

        if "auslaenderbehoerde" in prompt.lower() or "immigration" in prompt.lower():
            return {
                "suggested_folder": "Government",
                "reasoning": "Email from immigration office",
                "priority_score": 80,
                "confidence": 0.90
            }

        if "client" in prompt.lower() or "project" in prompt.lower():
            return {
                "suggested_folder": "Clients",
                "reasoning": "Email related to client projects",
                "priority_score": 70,
                "confidence": 0.85
            }

        if "newsletter" in prompt.lower() or "unsubscribe" in prompt.lower():
            return {
                "suggested_folder": "Newsletters",
                "reasoning": "Marketing or newsletter email",
                "priority_score": 20,
                "confidence": 0.75
            }

        if "urgent" in prompt.lower() or "wichtig" in prompt.lower():
            return {
                "suggested_folder": "Government",
                "reasoning": "Urgent email requiring immediate attention",
                "priority_score": 90,
                "confidence": 0.88
            }

        # Default: unclassified
        return {
            "suggested_folder": "Unclassified",
            "reasoning": "Unable to determine specific category",
            "priority_score": 50,
            "confidence": 0.5
        }

    def receive_completion(self, prompt: str, operation: str = "general") -> Dict[str, Any]:
        """Mock receive_completion method to match LLMClient interface.

        IMPORTANT: This is a SYNCHRONOUS method to match the real LLMClient API.
        The real LLMClient.receive_completion is sync, not async.

        This method provides deterministic classification responses based on
        email content patterns, without making real API calls.

        Args:
            prompt: Prompt to send to the LLM
            operation: Operation type (unused in mock)

        Returns:
            dict: Classification response matching classify_email format
        """
        # Track call for assertions
        self.calls.append({
            "method": "receive_completion",
            "prompt": prompt,
            "operation": operation
        })

        # Handle failure mode
        self._current_call_count += 1
        if self._failure_exception and self._current_call_count <= self._failure_count:
            raise self._failure_exception

        # Check for custom responses first
        for pattern, response in self._custom_responses.items():
            if pattern in prompt.lower():
                return response

        # Deterministic responses based on content patterns
        if "finanzamt" in prompt.lower() or "tax" in prompt.lower():
            return {
                "suggested_folder": "Government",
                "reasoning": "Email from tax office regarding official tax documents",
                "priority_score": 85,
                "confidence": 0.92
            }

        if "auslaenderbehoerde" in prompt.lower() or "immigration" in prompt.lower():
            return {
                "suggested_folder": "Government",
                "reasoning": "Email from immigration office",
                "priority_score": 80,
                "confidence": 0.90
            }

        if "client" in prompt.lower() or "project" in prompt.lower():
            return {
                "suggested_folder": "Clients",
                "reasoning": "Email related to client projects",
                "priority_score": 70,
                "confidence": 0.85
            }

        if "newsletter" in prompt.lower() or "unsubscribe" in prompt.lower():
            return {
                "suggested_folder": "Newsletters",
                "reasoning": "Marketing or newsletter email",
                "priority_score": 20,
                "confidence": 0.75
            }

        if "urgent" in prompt.lower() or "wichtig" in prompt.lower():
            return {
                "suggested_folder": "Government",
                "reasoning": "Urgent email requiring immediate attention",
                "priority_score": 90,
                "confidence": 0.88
            }

        # Default: unclassified
        return {
            "suggested_folder": "Unclassified",
            "reasoning": "Unable to determine specific category",
            "priority_score": 50,
            "confidence": 0.5
        }

    def get_call_count(self) -> int:
        """Return total number of API calls made."""
        return len(self.calls)

    def get_last_call(self) -> Dict[str, Any] | None:
        """Return details of the most recent API call."""
        return self.calls[-1] if self.calls else None

    def reset_calls(self):
        """Clear call tracking history."""
        self.calls.clear()
