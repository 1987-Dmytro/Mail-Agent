"""Unit tests for monitoring and alerting (Story 3.2).

Tests cover:
- send_admin_alert utility function
- ErrorAlertingMiddleware for error handling and alerting
"""

import pytest
from unittest.mock import AsyncMock, Mock, MagicMock
from fastapi import Request
from starlette.responses import Response

from app.utils.admin_alert import send_admin_alert
from app.core.middleware import ErrorAlertingMiddleware


class TestSendAdminAlert:
    """Tests for send_admin_alert utility (Story 3.2)."""

    @pytest.mark.asyncio
    async def test_send_admin_alert_success(self, mocker):
        """Test sending admin alert successfully via Telegram."""
        # Arrange
        mock_telegram = AsyncMock()
        mock_telegram.initialize = AsyncMock()
        mock_telegram.send_message = AsyncMock(return_value=12345)

        mocker.patch(
            "app.core.telegram_bot.TelegramBotClient",
            return_value=mock_telegram
        )
        mocker.patch.dict(
            "os.environ",
            {"ADMIN_TELEGRAM_CHAT_ID": "123456789"}
        )

        # Act
        result = await send_admin_alert(
            message="Test alert",
            severity="error",
            context={"error": "test error"},
            send_telegram=True
        )

        # Assert
        assert result is True
        mock_telegram.send_message.assert_called_once()
        call_args = mock_telegram.send_message.call_args
        assert "123456789" == call_args.kwargs["telegram_id"]
        assert "ERROR" in call_args.kwargs["text"]
        assert "Test alert" in call_args.kwargs["text"]

    @pytest.mark.asyncio
    async def test_send_admin_alert_no_chat_id_configured(self, mocker):
        """Test send_admin_alert when ADMIN_TELEGRAM_CHAT_ID is not configured."""
        # Arrange
        mocker.patch.dict("os.environ", {}, clear=True)

        # Act
        result = await send_admin_alert(
            message="Test alert",
            severity="error",
            send_telegram=True
        )

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_send_admin_alert_telegram_disabled(self, mocker):
        """Test send_admin_alert when Telegram is disabled."""
        # Act
        result = await send_admin_alert(
            message="Test alert",
            severity="warning",
            send_telegram=False
        )

        # Assert
        assert result is True  # Alert logged successfully

    @pytest.mark.asyncio
    async def test_send_admin_alert_severity_levels(self, mocker):
        """Test send_admin_alert with different severity levels."""
        # Arrange
        mock_telegram = AsyncMock()
        mock_telegram.initialize = AsyncMock()
        mock_telegram.send_message = AsyncMock(return_value=12345)

        mocker.patch(
            "app.core.telegram_bot.TelegramBotClient",
            return_value=mock_telegram
        )
        mocker.patch.dict(
            "os.environ",
            {"ADMIN_TELEGRAM_CHAT_ID": "123456789"}
        )

        severities = ["info", "warning", "error", "critical"]

        for severity in severities:
            # Act
            result = await send_admin_alert(
                message=f"Test {severity} alert",
                severity=severity,
                send_telegram=True
            )

            # Assert
            assert result is True


class TestErrorAlertingMiddleware:
    """Tests for ErrorAlertingMiddleware (Story 3.2)."""

    @pytest.mark.asyncio
    async def test_middleware_passes_through_successful_requests(self):
        """Test middleware doesn't interfere with successful requests."""
        # Arrange
        middleware = ErrorAlertingMiddleware(app=MagicMock())
        request = Mock(spec=Request)
        request.method = "GET"
        request.url.path = "/test"

        async def call_next(req):
            return Response(content="OK", status_code=200)

        # Act
        response = await middleware.dispatch(request, call_next)

        # Assert
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_middleware_alerts_on_server_error(self, mocker):
        """Test middleware sends alert on server errors."""
        # Arrange
        middleware = ErrorAlertingMiddleware(app=MagicMock())
        request = Mock(spec=Request)
        request.method = "POST"
        request.url.path = "/api/test"

        mock_send_alert = AsyncMock(return_value=True)
        mocker.patch(
            "app.utils.admin_alert.send_admin_alert",
            mock_send_alert
        )

        async def call_next(req):
            raise RuntimeError("Database connection failed")

        # Act & Assert
        with pytest.raises(RuntimeError):
            await middleware.dispatch(request, call_next)

        # Verify alert was sent
        mock_send_alert.assert_called_once()
        call_args = mock_send_alert.call_args
        assert "Unhandled exception" in call_args.kwargs["message"]
        assert call_args.kwargs["severity"] == "error"

    @pytest.mark.asyncio
    async def test_middleware_does_not_alert_on_validation_errors(self, mocker):
        """Test middleware doesn't alert on validation errors."""
        # Arrange
        middleware = ErrorAlertingMiddleware(app=MagicMock())
        request = Mock(spec=Request)
        request.method = "POST"
        request.url.path = "/api/test"

        mock_send_alert = AsyncMock(return_value=True)
        mocker.patch(
            "app.utils.admin_alert.send_admin_alert",
            mock_send_alert
        )

        async def call_next(req):
            raise ValueError("Invalid input")

        # Act & Assert
        with pytest.raises(ValueError):
            await middleware.dispatch(request, call_next)

        # Verify alert was NOT sent (ValueError is excluded)
        mock_send_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_middleware_continues_on_alert_failure(self, mocker):
        """Test middleware continues even if alert sending fails."""
        # Arrange
        middleware = ErrorAlertingMiddleware(app=MagicMock())
        request = Mock(spec=Request)
        request.method = "GET"
        request.url.path = "/api/test"

        # Mock alert to fail
        mock_send_alert = AsyncMock(side_effect=Exception("Telegram error"))
        mocker.patch(
            "app.utils.admin_alert.send_admin_alert",
            mock_send_alert
        )

        async def call_next(req):
            raise RuntimeError("Original error")

        # Act & Assert
        # Should still raise the original error, not the alert error
        with pytest.raises(RuntimeError, match="Original error"):
            await middleware.dispatch(request, call_next)
