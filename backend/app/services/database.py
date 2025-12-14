"""This file contains the database service for the application."""

from typing import (
    List,
    Optional,
)

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel import (
    SQLModel,
    select,
)

from app.core.config import (
    Environment,
    settings,
)
from app.core.logging import logger
from app.models.session import Session as ChatSession
from app.models.user import User


class DatabaseService:
    """Service class for database operations.

    This class handles all database operations for Users, Sessions, and Messages.
    It uses SQLModel for ORM operations and maintains a connection pool.
    """

    def __init__(self):
        """Initialize database service with connection pool."""
        self.engine = None
        self.async_session = None
        try:
            # Configure environment-specific database connection pool settings
            pool_size = settings.POSTGRES_POOL_SIZE
            max_overflow = settings.POSTGRES_MAX_OVERFLOW

            # Create async engine with appropriate pool configuration
            # Use postgresql+psycopg for async driver (psycopg3)
            # Prefer DATABASE_URL (Koyeb, Fly.io) over individual settings
            import os
            database_url = os.getenv("DATABASE_URL")
            if database_url:
                # Fix postgres:// -> postgresql:// for SQLAlchemy 2.0+
                database_url = database_url.replace("postgres://", "postgresql://")
                # Add async driver
                if "postgresql://" in database_url and "+psycopg" not in database_url:
                    connection_url = database_url.replace("postgresql://", "postgresql+psycopg://")
                else:
                    connection_url = database_url
            else:
                # Fallback to individual settings for local development
                connection_url = (
                    f"postgresql+psycopg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
                    f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
                )

            self.engine = create_async_engine(
                connection_url,
                pool_pre_ping=True,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=30,  # Connection timeout (seconds)
                pool_recycle=1800,  # Recycle connections after 30 minutes
            )

            # Create async session maker
            self.async_session = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            logger.info(
                "database_initialized",
                environment=settings.ENVIRONMENT.value,
                pool_size=pool_size,
                max_overflow=max_overflow,
            )
        except SQLAlchemyError as e:
            logger.warning(
                "database_initialization_skipped",
                error=str(e),
                environment=settings.ENVIRONMENT.value,
                message="Database configuration issue",
            )
            # Don't raise - allow app to start even without database

    async def create_user(
        self,
        email: str,
        password: str | None = None,
        gmail_oauth_token: str | None = None,
        gmail_refresh_token: str | None = None
    ) -> User:
        """Create a new user.

        Args:
            email: User's email address
            password: Hashed password (optional for OAuth users)
            gmail_oauth_token: Encrypted Gmail OAuth access token (optional)
            gmail_refresh_token: Encrypted Gmail OAuth refresh token (optional)

        Returns:
            User: The created user
        """
        async with self.async_session() as session:
            user = User(
                email=email,
                hashed_password=password,
                gmail_oauth_token=gmail_oauth_token,
                gmail_refresh_token=gmail_refresh_token,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info("user_created", email=email, has_oauth=bool(gmail_oauth_token))
            return user

    async def get_user(self, user_id: int) -> Optional[User]:
        """Get a user by ID.

        Args:
            user_id: The ID of the user to retrieve

        Returns:
            Optional[User]: The user if found, None otherwise
        """
        async with self.async_session() as session:
            user = await session.get(User, user_id)
            return user

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email.

        Args:
            email: The email of the user to retrieve

        Returns:
            Optional[User]: The user if found, None otherwise
        """
        async with self.async_session() as session:
            statement = select(User).where(User.email == email)
            result = await session.execute(statement)
            user = result.scalar_one_or_none()
            return user

    async def update_user(self, user: User) -> User:
        """Update an existing user.

        Args:
            user: The user model with updated fields

        Returns:
            User: The updated user
        """
        async with self.async_session() as session:
            # Merge the detached user object into the session
            user = await session.merge(user)
            await session.commit()
            await session.refresh(user)
            logger.info("user_updated", user_id=user.id)
            return user

    async def delete_user_by_email(self, email: str) -> bool:
        """Delete a user by email.

        Args:
            email: The email of the user to delete

        Returns:
            bool: True if deletion was successful, False if user not found
        """
        async with self.async_session() as session:
            statement = select(User).where(User.email == email)
            result = await session.execute(statement)
            user = result.scalar_one_or_none()
            if not user:
                return False

            await session.delete(user)
            await session.commit()
            logger.info("user_deleted", email=email)
            return True

    async def create_session(self, session_id: str, user_id: int, name: str = "") -> ChatSession:
        """Create a new chat session.

        Args:
            session_id: The ID for the new session
            user_id: The ID of the user who owns the session
            name: Optional name for the session (defaults to empty string)

        Returns:
            ChatSession: The created session
        """
        async with self.async_session() as session:
            chat_session = ChatSession(id=session_id, user_id=user_id, name=name)
            session.add(chat_session)
            await session.commit()
            await session.refresh(chat_session)
            logger.info("session_created", session_id=session_id, user_id=user_id, name=name)
            return chat_session

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session by ID.

        Args:
            session_id: The ID of the session to delete

        Returns:
            bool: True if deletion was successful, False if session not found
        """
        async with self.async_session() as session:
            chat_session = await session.get(ChatSession, session_id)
            if not chat_session:
                return False

            await session.delete(chat_session)
            await session.commit()
            logger.info("session_deleted", session_id=session_id)
            return True

    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a session by ID.

        Args:
            session_id: The ID of the session to retrieve

        Returns:
            Optional[ChatSession]: The session if found, None otherwise
        """
        async with self.async_session() as session:
            chat_session = await session.get(ChatSession, session_id)
            return chat_session

    async def get_user_sessions(self, user_id: int) -> List[ChatSession]:
        """Get all sessions for a user.

        Args:
            user_id: The ID of the user

        Returns:
            List[ChatSession]: List of user's sessions
        """
        async with self.async_session() as session:
            statement = select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.created_at)
            result = await session.execute(statement)
            sessions = result.scalars().all()
            return list(sessions)

    async def update_session_name(self, session_id: str, name: str) -> ChatSession:
        """Update a session's name.

        Args:
            session_id: The ID of the session to update
            name: The new name for the session

        Returns:
            ChatSession: The updated session

        Raises:
            HTTPException: If session is not found
        """
        async with self.async_session() as session:
            chat_session = await session.get(ChatSession, session_id)
            if not chat_session:
                raise HTTPException(status_code=404, detail="Session not found")

            chat_session.name = name
            session.add(chat_session)
            await session.commit()
            await session.refresh(chat_session)
            logger.info("session_name_updated", session_id=session_id, name=name)
            return chat_session

    def get_session_maker(self):
        """Get a session maker for creating database sessions.

        Returns:
            async_sessionmaker: An async session maker for database operations
        """
        return self.async_session

    async def health_check(self) -> dict:
        """Check database connection health (Story 3.5).

        Returns:
            dict: Status dict with 'status' key:
                - 'healthy': Database connection working
                - 'unhealthy': Database configured but connection failed
                - 'not_configured': Database not initialized
        """
        if self.engine is None or self.async_session is None:
            return {"status": "not_configured", "message": "Database not initialized"}

        try:
            async with self.async_session() as session:
                # Execute a simple query to check connection
                result = await session.execute(select(1))
                result.scalar()
                return {"status": "healthy", "message": "Database connection successful"}
        except Exception as e:
            logger.error("database_health_check_failed", error=str(e))
            return {"status": "unhealthy", "message": f"Database connection failed: {str(e)}"}


# Create a singleton instance
database_service = DatabaseService()
