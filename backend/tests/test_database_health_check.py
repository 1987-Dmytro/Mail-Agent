"""Unit tests for database health check (Story 3.5).

Tests cover:
- Database health_check method returns correct status
- Health endpoint properly displays database status
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.services.database import DatabaseService


class TestDatabaseHealthCheck:
    """Tests for DatabaseService.health_check() (Story 3.5)."""

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, mocker):
        """Test health_check returns healthy when database works."""
        # Arrange
        db_service = DatabaseService()

        # Mock the async_session to work properly
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalar = Mock(return_value=1)
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_maker = Mock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)

        db_service.async_session = mock_session_maker
        db_service.engine = Mock()  # Just needs to not be None

        # Act
        result = await db_service.health_check()

        # Assert
        assert result["status"] == "healthy"
        assert "successful" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_health_check_not_configured(self):
        """Test health_check returns not_configured when engine is None."""
        # Arrange
        db_service = DatabaseService()
        db_service.engine = None
        db_service.async_session = None

        # Act
        result = await db_service.health_check()

        # Assert
        assert result["status"] == "not_configured"
        assert "not initialized" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, mocker):
        """Test health_check returns unhealthy when query fails."""
        # Arrange
        db_service = DatabaseService()

        # Mock the async_session to raise an exception
        mock_session_maker = Mock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(
            side_effect=Exception("Connection refused")
        )

        db_service.async_session = mock_session_maker
        db_service.engine = Mock()  # Just needs to not be None

        # Act
        result = await db_service.health_check()

        # Assert
        assert result["status"] == "unhealthy"
        assert "failed" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_health_check_returns_dict(self):
        """Test health_check always returns a dict with status key."""
        # Arrange
        db_service = DatabaseService()
        db_service.engine = None
        db_service.async_session = None

        # Act
        result = await db_service.health_check()

        # Assert
        assert isinstance(result, dict)
        assert "status" in result
        assert "message" in result
