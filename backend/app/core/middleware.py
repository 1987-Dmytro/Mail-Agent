"""Custom middleware for tracking metrics and other cross-cutting concerns."""

import time
import traceback
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import structlog

from app.core.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    db_connections,
)

logger = structlog.get_logger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for tracking HTTP request metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Track metrics for each request.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            Response: The response from the application
        """
        start_time = time.time()

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            raise
        finally:
            duration = time.time() - start_time

            # Record metrics
            http_requests_total.labels(method=request.method, endpoint=request.url.path, status=status_code).inc()

            http_request_duration_seconds.labels(method=request.method, endpoint=request.url.path).observe(duration)

        return response


class ErrorAlertingMiddleware(BaseHTTPMiddleware):
    """Middleware for catching and alerting on critical errors (Story 3.2)."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Catch errors and send admin alerts for critical issues.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            Response: The response from the application (or error response)
        """
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # Log the error with full context
            error_context = {
                "method": request.method,
                "path": str(request.url.path),
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc()
            }

            logger.error(
                "unhandled_exception_in_request",
                **error_context
            )

            # Send admin alert for 5xx errors (server errors)
            # Import here to avoid circular dependencies
            from app.utils.admin_alert import send_admin_alert

            # Only alert on critical server errors, not validation errors
            if not isinstance(e, (ValueError, KeyError)):
                try:
                    await send_admin_alert(
                        message=f"Unhandled exception in {request.method} {request.url.path}",
                        severity="error",
                        context={
                            "error": str(e),
                            "type": type(e).__name__,
                            "path": str(request.url.path),
                            "method": request.method
                        },
                        send_telegram=True
                    )
                except Exception as alert_error:
                    # Don't let alert failures crash the app
                    logger.warning(
                        "failed_to_send_error_alert",
                        alert_error=str(alert_error)
                    )

            # Re-raise the exception to be handled by FastAPI's exception handlers
            raise
