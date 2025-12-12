"""Prometheus metrics configuration for the application.

This module sets up and configures Prometheus metrics for monitoring the application.
"""

from prometheus_client import Counter, Histogram, Gauge
from starlette_prometheus import metrics, PrometheusMiddleware

# Request metrics
http_requests_total = Counter("http_requests_total", "Total number of HTTP requests", ["method", "endpoint", "status"])

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds", "HTTP request duration in seconds", ["method", "endpoint"]
)

# Database metrics
db_connections = Gauge("db_connections", "Number of active database connections")

# Custom business metrics
orders_processed = Counter("orders_processed_total", "Total number of orders processed")

llm_inference_duration_seconds = Histogram(
    "llm_inference_duration_seconds",
    "Time spent processing LLM inference",
    ["model"],
    buckets=[0.1, 0.3, 0.5, 1.0, 2.0, 5.0]
)



llm_stream_duration_seconds = Histogram(
    "llm_stream_duration_seconds",
    "Time spent processing LLM stream inference",
    ["model"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# Gemini-specific metrics (also used for GROQ)
gemini_token_usage_total = Counter(
    "gemini_token_usage_total",
    "Total tokens consumed by LLM API calls (Gemini/GROQ)",
    ["token_type", "model"]  # token_type: prompt/completion, model: gemini-2.5-pro/llama-3.3-70b-versatile
)

# Error handling and recovery metrics (Story 2.11 - Task 9)
email_processing_errors_total = Counter(
    "email_processing_errors_total",
    "Total number of email processing errors",
    ["error_type", "user_id"]
)

email_dlq_total = Counter(
    "email_dlq_total",
    "Total number of emails moved to Dead Letter Queue",
    ["error_type", "user_id"]
)

email_retry_attempts_total = Counter(
    "email_retry_attempts_total",
    "Total number of retry attempts (successful and failed)",
    ["operation", "success"]
)

email_retry_count_histogram = Histogram(
    "email_retry_count_histogram",
    "Distribution of retry counts before success or failure",
    buckets=[0, 1, 2, 3, 4, 5]
)

email_error_recovery_duration_seconds = Histogram(
    "email_error_recovery_duration_seconds",
    "Time from error occurrence to successful retry",
    ["error_type"],
    buckets=[60, 300, 600, 1800, 3600, 7200]  # 1min, 5min, 10min, 30min, 1hr, 2hr
)

# Current error state metrics (gauges)
emails_in_error_state = Gauge(
    "emails_in_error_state",
    "Current number of emails in error state",
    ["error_type"]
)


def setup_metrics(app):
    """Set up Prometheus metrics middleware and endpoints.

    Args:
        app: FastAPI application instance
    """
    # Add Prometheus middleware
    app.add_middleware(PrometheusMiddleware)

    # Add metrics endpoint
    app.add_route("/metrics", metrics)
