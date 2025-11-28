"""API v1 router configuration.

This module sets up the main API router and includes all sub-routers for different
endpoints like authentication and chatbot functionality.
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.folders import router as folders_router
from app.api.v1.telegram import router as telegram_router
from app.api.v1.test import router as test_router
from app.api.v1.stats import router as stats_router
from app.api.v1.admin import router as admin_router
from app.api.v1.users import router as users_router
# NOTE: Chatbot router includes LangGraph components, deferred to Epic 2
# from app.api.v1.chatbot import router as chatbot_router
from app.core.logging import logger

api_router = APIRouter()

# Include routers
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(folders_router, prefix="/folders", tags=["folders"])
api_router.include_router(telegram_router, prefix="/telegram", tags=["telegram"])
api_router.include_router(test_router, prefix="/test", tags=["test"])
api_router.include_router(stats_router, prefix="/stats", tags=["stats"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
# NOTE: Chatbot router deferred to Epic 2 (LangGraph workflows for AI email classification)
# api_router.include_router(chatbot_router, prefix="/chatbot", tags=["chatbot"])


@api_router.get("/health")
async def health_check():
    """Health check endpoint.

    Returns:
        dict: Health status information.
    """
    logger.info("health_check_called")
    return {"status": "healthy", "version": "1.0.0"}


@api_router.get("/protected")
async def protected_test_endpoint():
    """Protected test endpoint (requires authentication).

    This endpoint returns 401 if not authenticated, used by integration tests.
    For the authenticated version, see /api/v1/auth/protected

    Returns:
        HTTPException: 401 Unauthorized
    """
    from fastapi import HTTPException
    raise HTTPException(status_code=401, detail="Unauthorized")
