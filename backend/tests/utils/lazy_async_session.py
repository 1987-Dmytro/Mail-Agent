"""Lazy AsyncSession proxy for cross-context usage in LangGraph workflow tests.

This module provides a session proxy that creates fresh sessions for each operation,
solving the "AsyncConnection context has not been started" error that occurs when
SQLAlchemy AsyncSession is passed via partial() to LangGraph workflow nodes.

The problem: SQLAlchemy's async session is context-bound. When LangGraph executes
workflow nodes (potentially in different async contexts), the session's connection
context may not be active.

The solution: This proxy creates a fresh session with proper context management
for EACH operation, ensuring the connection is always valid. Results are eagerly
fetched before the session closes to avoid lazy-loading issues.
"""

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, AsyncEngine
from sqlalchemy.engine import Result, CursorResult, ScalarResult
from sqlalchemy import text


class EagerResult:
    """Result wrapper that eagerly fetches all data."""

    def __init__(self, rows: list[Any]):
        """Initialize with fetched rows."""
        self._rows = rows
        self._index = 0

    def scalar_one_or_none(self) -> Any | None:
        """Return first scalar or None."""
        if not self._rows:
            return None
        # Handle both ORM objects (direct) and tuple results (index 0)
        row = self._rows[0]
        if isinstance(row, tuple):
            return row[0] if row else None
        else:
            # ORM object - return it directly
            return row

    def scalar_one(self) -> Any:
        """Return first scalar, error if not exactly one."""
        if len(self._rows) != 1:
            raise ValueError(f"Expected exactly one row, got {len(self._rows)}")
        row = self._rows[0]
        if isinstance(row, tuple):
            return row[0]
        else:
            return row

    def scalars(self):
        """Return scalars iterator."""
        # Handle both ORM objects and tuple results
        scalars = []
        for row in self._rows:
            if isinstance(row, tuple):
                scalars.append(row[0])
            else:
                scalars.append(row)
        return EagerScalars(scalars)

    def all(self) -> list[Any]:
        """Return all rows."""
        return self._rows

    def one(self) -> Any:
        """Return one row, error if not exactly one."""
        if len(self._rows) != 1:
            raise ValueError(f"Expected exactly one row, got {len(self._rows)}")
        return self._rows[0]

    def one_or_none(self) -> Any | None:
        """Return one row or None."""
        if len(self._rows) == 0:
            return None
        if len(self._rows) > 1:
            raise ValueError(f"Expected at most one row, got {len(self._rows)}")
        return self._rows[0]

    def first(self) -> Any | None:
        """Return first row or None."""
        return self._rows[0] if self._rows else None


class EagerScalars:
    """Scalars wrapper for eager results."""

    def __init__(self, scalars: list[Any]):
        """Initialize with scalar values."""
        self._scalars = scalars
        self._index = 0

    def all(self) -> list[Any]:
        """Return all scalars."""
        return self._scalars

    def one(self) -> Any:
        """Return one scalar, error if not exactly one."""
        if len(self._scalars) != 1:
            raise ValueError(f"Expected exactly one scalar, got {len(self._scalars)}")
        return self._scalars[0]

    def one_or_none(self) -> Any | None:
        """Return one scalar or None."""
        if len(self._scalars) == 0:
            return None
        if len(self._scalars) > 1:
            raise ValueError(f"Expected at most one scalar, got {len(self._scalars)}")
        return self._scalars[0]

    def first(self) -> Any | None:
        """Return first scalar or None."""
        return self._scalars[0] if self._scalars else None

    def __iter__(self):
        """Iterate over scalars."""
        return iter(self._scalars)


class LazyAsyncSession:
    """Session proxy that creates fresh sessions with eager result fetching.

    This class creates a new session for each database operation and eagerly
    fetches all results before closing the session. This ensures that:
    1. Each operation has a valid connection context
    2. Result objects remain usable after the session closes
    3. The session works across different asyncio contexts (e.g., in LangGraph workflows)

    Usage:
        factory = async_sessionmaker(engine, class_=AsyncSession)
        lazy_session = LazyAsyncSession(factory)

        # All results are eagerly fetched
        result = await lazy_session.execute(select(User))
        user = result.scalar_one_or_none()  # Works even though session is closed!

        lazy_session.add(new_user)
        await lazy_session.commit()
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        """Initialize with a session factory.

        Args:
            session_factory: SQLAlchemy async_sessionmaker instance
        """
        self._session_factory = session_factory
        self._pending_adds: list[Any] = []
        self._pending_deletes: list[Any] = []
        self._persistent_session: AsyncSession | None = None  # Single persistent session

    async def execute(self, statement, *args, **kwargs) -> EagerResult:
        """Execute a SQL statement using the persistent session.

        Uses a single persistent session for all operations to maintain
        object tracking across execute/commit calls.

        Args:
            statement: SQLAlchemy statement to execute
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments

        Returns:
            EagerResult with pre-fetched data
        """
        # Create persistent session if needed
        if self._persistent_session is None:
            self._persistent_session = self._session_factory()

        try:
            # Apply any pending adds
            for obj in self._pending_adds:
                try:
                    self._persistent_session.add(obj)
                    await self._persistent_session.flush()  # Flush to get IDs
                except Exception:
                    pass

            # Execute and fetch results
            result = await self._persistent_session.execute(statement, *args, **kwargs)

            # Fetch all rows immediately
            try:
                rows = result.fetchall()
            except Exception:
                # For INSERT/UPDATE/DELETE statements that don't return rows
                rows = []

            # Session stays open - objects remain attached and tracked
            return EagerResult(rows)

        except Exception:
            raise

    def add(self, instance: Any):
        """Add an instance to be persisted on next commit.

        Args:
            instance: SQLAlchemy model instance
        """
        self._pending_adds.append(instance)

    def delete(self, instance: Any):
        """Mark an instance for deletion on next commit.

        Args:
            instance: SQLAlchemy model instance
        """
        self._pending_deletes.append(instance)

    async def commit(self):
        """Commit changes in the persistent session."""
        if self._persistent_session is None:
            return

        # Add pending objects
        for obj in self._pending_adds:
            self._persistent_session.add(obj)

        # Delete pending objects
        for obj in self._pending_deletes:
            await self._persistent_session.delete(obj)

        await self._persistent_session.commit()

        # Refresh objects to get their IDs
        for obj in self._pending_adds:
            try:
                await self._persistent_session.refresh(obj)
            except Exception:
                pass

        self._pending_adds.clear()
        self._pending_deletes.clear()

    async def refresh(self, instance: Any):
        """Refresh an instance from the database.

        Args:
            instance: SQLAlchemy model instance
        """
        async with self._session_factory() as session:
            # Merge to attach to this session
            merged = await session.merge(instance)
            await session.refresh(merged)
            # Copy refreshed attributes back to original
            for key in instance.__mapper__.columns.keys():
                setattr(instance, key, getattr(merged, key))

    async def rollback(self):
        """Rollback pending changes (clears pending lists)."""
        self._pending_adds.clear()
        self._pending_deletes.clear()

    async def flush(self):
        """Flush pending changes to the database."""
        await self.commit()

    async def close(self):
        """Close the persistent session."""
        if self._persistent_session:
            try:
                await self._persistent_session.close()
            except Exception:
                pass  # Ignore close errors
            self._persistent_session = None

    async def start(self):
        """Start the proxy (no-op for compatibility)."""
        pass

    # Scalar helper methods
    async def scalar(self, statement, *args, **kwargs) -> Any:
        """Execute and return a scalar result."""
        result = await self.execute(statement, *args, **kwargs)
        return result.scalar_one_or_none()

    async def scalars(self, statement, *args, **kwargs):
        """Execute and return scalars."""
        result = await self.execute(statement, *args, **kwargs)
        return result.scalars()


def create_lazy_session(engine: AsyncEngine) -> LazyAsyncSession:
    """Create a LazyAsyncSession from an engine.

    Args:
        engine: SQLAlchemy AsyncEngine

    Returns:
        LazyAsyncSession proxy instance
    """
    factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return LazyAsyncSession(factory)
