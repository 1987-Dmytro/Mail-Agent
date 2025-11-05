"""Health check endpoints for monitoring database and service status."""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.logging import logger
from app.services.database import database_service

router = APIRouter()


@router.get("/db", status_code=status.HTTP_200_OK)
async def check_database_health():
    """Check database connection health.

    This endpoint verifies that the database is reachable and responsive
    by executing a simple SELECT 1 query.

    Returns:
        JSON response with database status:
        - status: "connected" if database is healthy
        - database: name of the database
        - message: human-readable status message

        OR on failure:
        - status: "disconnected"
        - error: error details
        - message: human-readable error message

    Status Codes:
        200: Database is connected and healthy
        503: Database is disconnected or unreachable
    """
    logger.info("database_health_check_called")

    try:
        # Use the database service health check method
        is_healthy = await database_service.health_check()

        if is_healthy:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "connected",
                    "database": "mailagent",
                    "message": "PostgreSQL connection successful"
                }
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "disconnected",
                    "error": "Database connection failed",
                    "message": "Unable to connect to PostgreSQL"
                }
            )
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "disconnected",
                "error": str(e),
                "message": "Unable to connect to PostgreSQL"
            }
        )
