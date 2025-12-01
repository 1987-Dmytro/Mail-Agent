"""AsyncSession wrapper for cross-context usage in LangGraph workflow tests.

This wrapper solves the "AsyncConnection context has not been started" error
that occurs when passing SQLAlchemy AsyncSession via partial() to LangGraph
workflow nodes. LangGraph may execute nodes in a different asyncio context,
which breaks SQLAlchemy's context-local connection handling.

The wrapper ensures that database operations are always executed properly
by re-establishing the connection context when needed.
"""

from typing import Any, TypeVar, Sequence
from sqlalchemy import Select, Update, Delete, Insert
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine, async_sessionmaker
from sqlalchemy.engine import Result

T = TypeVar('T')


class CrossContextAsyncSession:
    """AsyncSession wrapper that works across asyncio contexts.

    This class wraps an async_sessionmaker and creates new sessions
    for each operation, ensuring the connection context is always valid.
    This is necessary for LangGraph workflow tests where the session
    is passed via partial() and used in different asyncio contexts.

    Usage in tests:
        wrapper = CrossContextAsyncSession(database_url)
        await wrapper.initialize()

        # Use wrapper like a regular session
        result = await wrapper.execute(select(User).where(User.id == 1))
        wrapper.add(new_user)
        await wrapper.commit()
    """

    def __init__(self, database_url: str):
        """Initialize wrapper with database URL.

        Args:
            database_url: SQLAlchemy async database URL
        """
        self._database_url = database_url
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
        self._current_session: AsyncSession | None = None
        self._pending_adds: list[Any] = []

    async def initialize(self):
        """Initialize engine and session factory."""
        self._engine = create_async_engine(
            self._database_url,
            echo=False,
            future=True,
        )
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def _get_session(self) -> AsyncSession:
        """Get or create a session for the current operation."""
        if self._current_session is None:
            self._current_session = self._session_factory()
        return self._current_session

    async def execute(self, statement: Select | Update | Delete | Insert, *args, **kwargs) -> Result:
        """Execute a SQL statement.

        Args:
            statement: SQLAlchemy statement to execute

        Returns:
            Result object from execution
        """
        session = await self._get_session()
        try:
            return await session.execute(statement, *args, **kwargs)
        except Exception as e:
            # If we get a context error, try creating a fresh session
            if "context has not been started" in str(e):
                await self._reset_session()
                session = await self._get_session()
                return await session.execute(statement, *args, **kwargs)
            raise

    def add(self, instance: Any):
        """Add an instance to the session.

        Args:
            instance: SQLAlchemy model instance
        """
        self._pending_adds.append(instance)

    async def commit(self):
        """Commit the current transaction."""
        session = await self._get_session()

        # Add any pending instances
        for instance in self._pending_adds:
            session.add(instance)
        self._pending_adds.clear()

        await session.commit()

    async def refresh(self, instance: Any):
        """Refresh an instance from the database.

        Args:
            instance: SQLAlchemy model instance
        """
        session = await self._get_session()
        await session.refresh(instance)

    async def rollback(self):
        """Rollback the current transaction."""
        if self._current_session:
            await self._current_session.rollback()

    async def _reset_session(self):
        """Close current session and prepare for a new one."""
        if self._current_session:
            try:
                await self._current_session.close()
            except Exception:
                pass
            self._current_session = None

    async def close(self):
        """Close the session and engine."""
        await self._reset_session()
        if self._engine:
            await self._engine.dispose()

    # Context manager support
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
