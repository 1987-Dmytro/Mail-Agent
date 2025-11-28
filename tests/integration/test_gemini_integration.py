"""Integration tests for Gemini API.

These tests validate:
- Real Gemini API connectivity (optional, requires API key)
- Test endpoint integration with mocked LLM client
- End-to-end request/response flow with authentication
"""

import os
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.llm_client import LLMClient
from app.main import app


# Integration test markers
pytestmark = pytest.mark.integration


class TestGeminiAPIRealCall:
    """Tests for actual Gemini API connectivity (requires API key)."""

    @pytest.mark.slow
    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY"),
        reason="GEMINI_API_KEY not set in test environment. Set it to enable real API tests.",
    )
    def test_gemini_api_real_call(self):
        """Test real Gemini API call with simple prompt.

        This test makes an actual API call to Gemini to validate connectivity.
        It's marked as @pytest.mark.slow and @pytest.mark.integration.

        To run this test:
        1. Set GEMINI_API_KEY environment variable
        2. Run: pytest tests/integration/test_gemini_integration.py -v -m integration

        Note: This test is optional and will be skipped if API key is not configured.
        """
        # Initialize real LLM client (will use GEMINI_API_KEY from env)
        client = LLMClient()

        # Make simple API call
        prompt = "Say 'Hello from Gemini API test' in exactly 5 words."
        response = client.send_prompt(prompt, response_format="text")

        # Verify response received
        assert response is not None
        assert len(response) > 0
        assert isinstance(response, str)

        # Verify token usage tracked
        stats = client.get_token_usage_stats()
        assert stats["total_tokens"] > 0
        assert stats["prompt_tokens"] > 0
        assert stats["completion_tokens"] > 0

    @pytest.mark.slow
    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY"),
        reason="GEMINI_API_KEY not set in test environment",
    )
    def test_gemini_api_json_mode_real(self):
        """Test real Gemini API call with JSON mode.

        Validates that JSON mode works correctly with actual API.
        """
        client = LLMClient()

        # Request JSON response
        prompt = 'Respond with JSON: {"status": "ok", "message": "test successful"}'
        response = client.receive_completion(prompt)

        # Verify JSON response
        assert isinstance(response, dict)
        # Gemini should return structured output (though exact format may vary)


class TestGeminiTestEndpoint:
    """Tests for /api/v1/test/gemini endpoint integration."""

    @pytest.fixture
    def mock_auth_user(self):
        """Mock authenticated user for testing."""
        from app.models.user import User

        user = User(
            id=1,
            email="test@example.com",
            username="testuser",
            hashed_password="fake_hash",
            is_active=True,
        )
        return user

    @pytest.fixture
    def client(self, mock_auth_user):
        """FastAPI TestClient with mocked authentication."""
        from app.api.v1.auth import get_current_user

        # Override the dependency
        app.dependency_overrides[get_current_user] = lambda: mock_auth_user
        client = TestClient(app)
        yield client
        # Clean up
        app.dependency_overrides.clear()

    def test_test_endpoint_integration_text_mode(self, client):
        """Test Gemini test endpoint with text mode and mocked LLM."""
        # Mock LLM client to avoid real API calls
        mock_llm_response = "This is a test response from Gemini."
        mock_token_stats = {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        }

        with patch("app.api.v1.test.LLMClient") as MockLLMClient:
            mock_client_instance = Mock()
            mock_client_instance.send_prompt.return_value = mock_llm_response
            mock_client_instance.get_token_usage_stats.return_value = mock_token_stats
            MockLLMClient.return_value = mock_client_instance

            # Make request to test endpoint (auth is mocked via dependency override)
            response = client.post(
                "/api/v1/test/gemini",
                json={
                    "prompt": "Test prompt",
                    "response_format": "text",
                },
            )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "response" in data["data"]
        assert data["data"]["response"]["response"] == mock_llm_response
        assert "tokens_used" in data["data"]
        assert data["data"]["tokens_used"] == 30
        assert "latency_ms" in data["data"]
        assert isinstance(data["data"]["latency_ms"], int)

    def test_test_endpoint_integration_json_mode(self, client):
        """Test Gemini test endpoint with JSON mode and mocked LLM."""
        # Mock LLM client JSON response
        mock_json_response = {
            "suggested_folder": "Government",
            "reasoning": "Tax office email",
            "priority_score": 85,
        }
        mock_token_stats = {
            "prompt_tokens": 15,
            "completion_tokens": 25,
            "total_tokens": 40,
        }

        with patch("app.api.v1.test.LLMClient") as MockLLMClient:
            mock_client_instance = Mock()
            mock_client_instance.receive_completion.return_value = mock_json_response
            mock_client_instance.get_token_usage_stats.return_value = mock_token_stats
            MockLLMClient.return_value = mock_client_instance

            # Make request with JSON mode
            response = client.post(
                "/api/v1/test/gemini",
                json={
                    "prompt": "Classify email: From tax@gov.de Subject: Tax deadline",
                    "response_format": "json",
                },
            )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["response"] == mock_json_response
        assert data["data"]["tokens_used"] == 40

    def test_test_endpoint_requires_authentication(self):
        """Test endpoint requires JWT authentication when no override is set."""
        # Create client without dependency override
        test_client = TestClient(app)

        # Make request without auth (should fail)
        response = test_client.post(
            "/api/v1/test/gemini",
            json={
                "prompt": "Test",
                "response_format": "text",
            },
        )

        # Should return 401, 403, or 422 (depending on how the endpoint validates auth)
        # Since auth is required, it should fail
        assert response.status_code in [401, 403, 422]

    def test_test_endpoint_invalid_response_format(self, client):
        """Test endpoint rejects invalid response_format."""
        response = client.post(
            "/api/v1/test/gemini",
            json={
                "prompt": "Test",
                "response_format": "invalid",
            },
        )

        # Should return 400 Bad Request
        assert response.status_code == 400
        assert "response_format must be 'text' or 'json'" in response.json()["detail"]
