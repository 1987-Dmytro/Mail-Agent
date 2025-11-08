"""This file contains the main application entry point."""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import (
    Any,
    Dict,
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
from app.core.middleware import MetricsMiddleware
from app.core.telegram_bot import TelegramBotClient
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    logger.info(
        "application_startup",
        project_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        api_prefix=settings.API_V1_STR,
    )

    # Initialize and start Telegram bot
    if settings.TELEGRAM_BOT_TOKEN:
        try:
            await telegram_bot.initialize()
            await telegram_bot.start_polling()
            logger.info("application_startup", telegram_bot="started")
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
            await telegram_bot.stop_polling()
            logger.info("application_shutdown", telegram_bot="stopped")
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


# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    """Health check endpoint with environment-specific information.

    Returns:
        Dict[str, Any]: Health status information
    """
    logger.info("health_check_called")

    # Check database connectivity (handle case where DB may not be set up yet)
    try:
        db_healthy = await database_service.health_check()
    except Exception as e:
        logger.warning("database_not_configured", error=str(e))
        db_healthy = False

    response = {
        "status": "healthy" if db_healthy else "degraded",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT.value,
        "components": {"api": "healthy", "database": "healthy" if db_healthy else "not_configured"},
        "timestamp": datetime.now().isoformat(),
    }

    # API is healthy even if DB isn't configured yet (for Story 1.2)
    # DB will be set up in Story 1.3
    status_code = status.HTTP_200_OK

    return JSONResponse(content=response, status_code=status_code)
