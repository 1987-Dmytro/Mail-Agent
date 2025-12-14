"""Shared dependencies for API endpoints."""

from typing import Generator, AsyncGenerator

from sqlmodel import Session, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import settings

# Determine database URL
# If DATABASE_URL is set (e.g., from Koyeb/Heroku), use it directly
# Otherwise, construct from individual POSTGRES_* variables
if settings.DATABASE_URL:
    # DATABASE_URL format: postgres://user:pass@host:port/dbname
    # Convert postgres:// to postgresql:// for SQLAlchemy compatibility
    sync_db_url = settings.DATABASE_URL.replace("postgres://", "postgresql://", 1)
    async_db_url = settings.DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
else:
    # Construct from individual variables (for local development)
    sync_db_url = (
        f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )
    async_db_url = (
        f"postgresql+psycopg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )

# Create synchronous engine for database operations
# Used for telegram linking and other sync operations
engine = create_engine(
    sync_db_url,
    echo=False,
    pool_pre_ping=True,
)

# Create async engine for async operations (Telegram bot handlers, workflows)
async_engine = create_async_engine(
    async_db_url,
    echo=False,
    pool_pre_ping=True,
)

# Async session maker for creating async sessions
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Dependency that provides a database session.

    Yields:
        Session: SQLModel database session

    Example:
        @router.post("/example")
        async def example_endpoint(db: Session = Depends(get_db)):
            # Use db session here
            pass
    """
    with Session(engine) as session:
        yield session


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an async database session.

    Yields:
        AsyncSession: Async SQLAlchemy database session

    Example:
        @router.post("/example")
        async def example_endpoint(db: AsyncSession = Depends(get_async_db)):
            # Use async db session here
            pass
    """
    async with AsyncSessionLocal() as session:
        yield session
