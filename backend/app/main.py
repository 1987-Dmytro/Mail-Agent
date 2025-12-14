"""This file contains the main application entry point."""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import (
    Any,
    Dict,
    Optional,
)

from dotenv import load_dotenv
from fastapi import (
    FastAPI,
    Request,
    status,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
# NOTE: Langfuse integration deferred to Epic 2 (LangGraph workflows)
# from langfuse import Langfuse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import logger
from app.core.metrics import setup_metrics
from app.core.middleware import MetricsMiddleware, ErrorAlertingMiddleware
from app.core.telegram_bot import TelegramBotClient
from app.core.vector_db import VectorDBClient  # ChromaDB (legacy)
from app.core.vector_db_pinecone import PineconeVectorDBClient  # Pinecone (production)
from app.services.database import database_service
from app.utils.errors import TelegramBotError

# Load environment variables
load_dotenv()

# NOTE: Langfuse initialization deferred to Epic 2
# Will be enabled when we implement LangGraph workflows for AI email classification
# langfuse = Langfuse(
#     public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
#     secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
#     host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
# )

# Global Telegram bot instance
telegram_bot = TelegramBotClient()

# Global Vector DB client instance (Pinecone in production, ChromaDB for local dev)
vector_db_client: Optional[PineconeVectorDBClient] = None


def initialize_email_embeddings_collection() -> None:
    """Initialize Pinecone vector database for email embeddings.

    Creates connection to Pinecone cloud index with namespace isolation for Mail Agent emails.
    Uses existing "ai-assistant-memories" index with "mail-agent-emails" namespace.

    Metadata schema:
        - message_id: Gmail message ID (str)
        - thread_id: Gmail thread ID (str)
        - sender: Email sender address (str)
        - date: Email timestamp in ISO 8601 format (str)
        - subject: Email subject line (str)
        - language: Detected language code: ru/uk/en/de (str)
        - snippet: First 200 chars of email body (str)

    Raises:
        ConnectionError: If Pinecone initialization fails
    """
    global vector_db_client

    try:
        # Check if PINECONE_API_KEY is set
        pinecone_api_key = os.getenv("PINECONE_API_KEY")

        if pinecone_api_key:
            # Production: Use Pinecone cloud vector database
            logger.info(
                "pinecone_initialization_started",
                index_name="ai-assistant-memories",
                namespace="mail-agent-emails",
                api_key_prefix=pinecone_api_key[:10] + "..."
            )

            try:
                vector_db_client = PineconeVectorDBClient(
                    api_key=pinecone_api_key,
                    index_name="ai-assistant-memories",  # Existing 768-dim index
                    namespace="mail-agent-emails"  # Isolated namespace
                )

                # Verify Pinecone connection health
                if not vector_db_client.health_check():
                    raise ConnectionError("Pinecone health check failed - connection not working")

                # Create email_embeddings collection (namespace)
                collection = vector_db_client.get_or_create_collection(
                    name="email_embeddings",
                    metadata={
                        "hnsw:space": "cosine",  # Cosine similarity
                        "description": "Email embeddings for RAG context retrieval",
                    },
                )

                embedding_count = vector_db_client.count_embeddings("email_embeddings")

                logger.info(
                    "vector_db_initialized",
                    provider="pinecone",
                    index_name="ai-assistant-memories",
                    namespace="mail-agent-emails",
                    collection_name="email_embeddings",
                    distance_metric="cosine",
                    collection_count=embedding_count,
                    status="SUCCESS"
                )

            except Exception as pinecone_error:
                # CRITICAL: Log Pinecone initialization failure with full traceback
                logger.error(
                    "pinecone_initialization_failed",
                    error=str(pinecone_error),
                    error_type=type(pinecone_error).__name__,
                    exc_info=True  # Include full traceback
                )
                logger.critical(
                    "falling_back_to_chromadb_due_to_pinecone_failure",
                    reason=str(pinecone_error),
                    warning="ChromaDB in cloud deployment = EPHEMERAL STORAGE! Data will be lost on restart!"
                )
                # Re-raise to prevent silent fallback in production
                raise

        else:
            # Fallback: Use ChromaDB for local development
            logger.warning(
                "pinecone_api_key_missing",
                note="Falling back to ChromaDB for local development. "
                     "Set PINECONE_API_KEY environment variable for production!"
            )
            vector_db_client = VectorDBClient(persist_directory=settings.CHROMADB_PATH)

            collection = vector_db_client.get_or_create_collection(
                name="email_embeddings",
                metadata={"hnsw:space": "cosine"},
            )

            logger.info(
                "vector_db_initialized",
                provider="chromadb",
                persist_directory=settings.CHROMADB_PATH,
                collection_count=vector_db_client.count_embeddings("email_embeddings"),
                warning="Using local ChromaDB - not suitable for production!"
            )

    except Exception as e:
        logger.error(
            "vector_db_initialization_failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True
        )
        # Allow app to start in degraded mode without vector DB
        # (similar to Telegram bot handling)
        logger.warning("application_starting_without_vector_db", degraded_mode=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    logger.info(
        "application_startup",
        project_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        api_prefix=settings.API_V1_STR,
    )

    # Initialize Pinecone vector database (Epic 3 - Story 3.1)
    initialize_email_embeddings_collection()

    # Initialize and start Telegram bot
    if settings.TELEGRAM_BOT_TOKEN:
        try:
            await telegram_bot.initialize()

            # Use webhook in production/staging, polling in development
            from app.core.config import Environment

            if settings.ENVIRONMENT in [Environment.PRODUCTION, Environment.STAGING]:
                # Webhook mode for production deployments
                await telegram_bot.start()  # Start app without polling

                # Configure webhook if URL is set
                if settings.TELEGRAM_WEBHOOK_URL:
                    await telegram_bot.set_webhook(
                        webhook_url=settings.TELEGRAM_WEBHOOK_URL,
                        secret_token=settings.TELEGRAM_WEBHOOK_SECRET,
                    )
                    logger.info(
                        "application_startup",
                        telegram_bot="started",
                        mode="webhook",
                        webhook_url=settings.TELEGRAM_WEBHOOK_URL,
                    )
                else:
                    logger.warning(
                        "telegram_webhook_url_not_configured",
                        note="TELEGRAM_WEBHOOK_URL not set - bot will not receive updates",
                    )
            else:
                # Polling mode for local development
                await telegram_bot.start_polling()
                logger.info(
                    "application_startup",
                    telegram_bot="started",
                    mode="polling",
                )

        except TelegramBotError as e:
            logger.error(
                "telegram_bot_startup_failed",
                error=str(e),
                note="Application will continue without Telegram bot",
            )
            # Allow app to start in degraded mode without bot
    else:
        logger.warning(
            "telegram_bot_not_configured",
            note="TELEGRAM_BOT_TOKEN not set - bot will not start",
        )

    yield

    # Stop Telegram bot gracefully
    if settings.TELEGRAM_BOT_TOKEN:
        try:
            from app.core.config import Environment

            if settings.ENVIRONMENT in [Environment.PRODUCTION, Environment.STAGING]:
                # Webhook mode shutdown
                await telegram_bot.stop()
                logger.info("application_shutdown", telegram_bot="stopped", mode="webhook")
            else:
                # Polling mode shutdown
                await telegram_bot.stop_polling()
                logger.info("application_shutdown", telegram_bot="stopped", mode="polling")
        except Exception as e:
            logger.error("telegram_bot_shutdown_failed", error=str(e))

    logger.info("application_shutdown")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Set up Prometheus metrics
setup_metrics(app)

# Add custom metrics middleware
app.add_middleware(MetricsMiddleware)

# Add error alerting middleware (Story 3.2)
app.add_middleware(ErrorAlertingMiddleware)

# Add CORS middleware - MUST BE LAST (executes first due to FastAPI middleware order)
# CRITICAL for frontend-backend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)

# Set up rate limiter exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Add validation exception handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors from request data.

    Args:
        request: The request that caused the validation error
        exc: The validation error

    Returns:
        JSONResponse: A formatted error response
    """
    # Log the validation error
    logger.error(
        "validation_error",
        client_host=request.client.host if request.client else "unknown",
        path=request.url.path,
        errors=str(exc.errors()),
    )

    # Format the errors to be more user-friendly
    formatted_errors = []
    for error in exc.errors():
        loc = " -> ".join([str(loc_part) for loc_part in error["loc"] if loc_part != "body"])
        formatted_errors.append({"field": loc, "message": error["msg"]})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": formatted_errors},
    )


# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["root"][0])
async def root(request: Request):
    """Root endpoint returning basic API information."""
    logger.info("root_endpoint_called")
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "healthy",
        "environment": settings.ENVIRONMENT.value,
        "swagger_url": "/docs",
        "redoc_url": "/redoc",
        "message": "Mail Agent Backend API",
    }


@app.get("/health")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["health"][0])
async def health_check(request: Request) -> Dict[str, Any]:
    """Health check endpoint with environment-specific information (Story 3.2).

    Returns:
        Dict[str, Any]: Health status information with component checks
    """
    logger.info("health_check_called")

    components = {"api": "healthy"}

    # Check database connectivity (Story 3.5 - improved status reporting)
    try:
        db_status = await database_service.health_check()
        components["database"] = db_status["status"]
        db_healthy = db_status["status"] == "healthy"
    except Exception as e:
        logger.warning("database_health_check_exception", error=str(e))
        components["database"] = "unhealthy"
        db_healthy = False

    # Check Redis connectivity (Story 3.2)
    try:
        import redis.asyncio as redis
        # Use REDIS_URL or extract base URL from CELERY_BROKER_URL (without query params)
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            # Fallback: extract base URL from CELERY_BROKER_URL (remove query params)
            celery_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
            redis_url = celery_url.split('?')[0]  # Remove ?ssl_cert_reqs=...

        redis_client = redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            ssl_cert_reqs=None if redis_url.startswith("rediss://") else None
        )
        await redis_client.ping()
        await redis_client.close()
        components["redis"] = "healthy"
        redis_healthy = True
    except Exception as e:
        logger.warning("redis_connection_failed", error=str(e))
        components["redis"] = "unhealthy"
        redis_healthy = False

    # Check Celery worker (Story 3.2)
    try:
        from app.celery import celery_app
        # Check if workers are active
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        if active_workers and len(active_workers) > 0:
            components["celery"] = "healthy"
            celery_healthy = True
        else:
            components["celery"] = "no_workers"
            celery_healthy = False
    except Exception as e:
        logger.warning("celery_check_failed", error=str(e))
        components["celery"] = "unhealthy"
        celery_healthy = False

    # Overall status (Story 3.2)
    all_healthy = db_healthy and redis_healthy and celery_healthy
    overall_status = "healthy" if all_healthy else "degraded"

    response = {
        "status": overall_status,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT.value,
        "components": components,
        "timestamp": datetime.now().isoformat(),
    }

    # Return 200 OK even if degraded (for Docker health check)
    status_code = status.HTTP_200_OK

    return JSONResponse(content=response, status_code=status_code)
