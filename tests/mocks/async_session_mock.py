"""Mock AsyncSession for workflow integration testing.

This mock provides a simplified async session that doesn't have the
async context limitations of real SQLAlchemy AsyncSession. It delegates
actual database operations to a real session while providing a stable
interface for workflow nodes.
"""

from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock
from sqlalchemy.ext.asyncio import AsyncSession


class MockAsyncSession:
    """Mock AsyncSession that wraps a real session for workflow tests.

    This mock solves the "AsyncConnection context has not been started"
    error that occurs when a real AsyncSession is passed via partial()
    to LangGraph workflow nodes.

    The mock tracks all operations and can be configured to return
    specific data for test assertions.
    """

    def __init__(self, real_session: AsyncSession = None):
        """Initialize mock session.

        Args:
            real_session: Optional real session to delegate to for actual DB ops
        """
        self._real_session = real_session
        self._execute_calls: List[Dict[str, Any]] = []
        self._add_calls: List[Any] = []
        self._commit_count: int = 0
        self._custom_results: Dict[str, Any] = {}
        self._models: Dict[type, Dict[int, Any]] = {}  # model_class -> {id: instance}

    def register_model(self, model: Any):
        """Register a model instance for later retrieval.

        Args:
            model: SQLAlchemy model instance with an 'id' attribute
        """
        model_class = type(model)
        if model_class not in self._models:
            self._models[model_class] = {}
        if hasattr(model, 'id') and model.id is not None:
            self._models[model_class][model.id] = model

    def register_models(self, models: List[Any]):
        """Register multiple model instances."""
        for model in models:
            self.register_model(model)

    async def execute(self, statement, *args, **kwargs):
        """Mock execute that returns configured results or queries registered models.

        Args:
            statement: SQLAlchemy statement to execute

        Returns:
            Mock result object with scalars() and scalar_one_or_none() methods
        """
        self._execute_calls.append({
            "statement": str(statement),
            "args": args,
            "kwargs": kwargs
        })

        # If we have a real session, delegate to it
        if self._real_session is not None:
            try:
                return await self._real_session.execute(statement, *args, **kwargs)
            except Exception:
                # If real session fails, fall back to mock behavior
                pass

        # Create mock result
        result = Mock()
        result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))
        result.scalar_one_or_none = Mock(return_value=None)
        result.scalar = Mock(return_value=None)

        # Try to extract model class and ID from statement for lookup
        stmt_str = str(statement)
        for model_class, instances in self._models.items():
            table_name = getattr(model_class, '__tablename__', model_class.__name__.lower())
            if table_name in stmt_str.lower():
                # Return all instances if it's a general query
                all_instances = list(instances.values())
                result.scalars = Mock(return_value=Mock(all=Mock(return_value=all_instances)))

                # Return first instance for scalar_one_or_none
                if all_instances:
                    result.scalar_one_or_none = Mock(return_value=all_instances[0])
                    result.scalar = Mock(return_value=all_instances[0])
                break

        return result

    def add(self, instance):
        """Mock add operation.

        Args:
            instance: Model instance to add
        """
        self._add_calls.append(instance)
        self.register_model(instance)

        # Delegate to real session if available
        if self._real_session is not None:
            self._real_session.add(instance)

    async def commit(self):
        """Mock commit operation."""
        self._commit_count += 1

        # Delegate to real session if available
        if self._real_session is not None:
            try:
                await self._real_session.commit()
            except Exception:
                pass

    async def refresh(self, instance):
        """Mock refresh operation.

        Args:
            instance: Model instance to refresh
        """
        # Delegate to real session if available
        if self._real_session is not None:
            try:
                await self._real_session.refresh(instance)
            except Exception:
                pass

    async def rollback(self):
        """Mock rollback operation."""
        if self._real_session is not None:
            try:
                await self._real_session.rollback()
            except Exception:
                pass

    async def close(self):
        """Mock close operation."""
        pass

    def get_execute_count(self) -> int:
        """Return number of execute calls."""
        return len(self._execute_calls)

    def get_add_count(self) -> int:
        """Return number of add calls."""
        return len(self._add_calls)

    def get_commit_count(self) -> int:
        """Return number of commit calls."""
        return self._commit_count
