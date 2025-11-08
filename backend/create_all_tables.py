"""Create all database tables from SQLModel definitions."""

import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

from app.models.user import User
from app.models.email import EmailProcessingQueue
from app.models.folder_category import FolderCategory
from app.models.linking_codes import LinkingCode
from app.models.workflow_mapping import WorkflowMapping
from app.models.notification_preferences import NotificationPreferences
from app.models.approval_history import ApprovalHistory


async def create_tables():
    """Create all tables in the database."""
    # Get database URL from environment or construct from PostgreSQL parameters
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        # Construct from individual parameters
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        user = os.getenv("POSTGRES_USER", "mailagent")
        password = os.getenv("POSTGRES_PASSWORD", "mailagent_dev_password_2024")
        database = os.getenv("POSTGRES_DB", "mailagent")
        db_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
    else:
        # Convert psycopg to asyncpg
        db_url = db_url.replace("postgresql+psycopg://", "postgresql+asyncpg://")
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    print(f"Using database URL: {db_url.replace(password if password else '', '***')}")
    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        # Drop all tables first
        print("Dropping all tables...")
        await conn.run_sync(SQLModel.metadata.drop_all)
        # Create all tables
        print("Creating all tables...")
        await conn.run_sync(SQLModel.metadata.create_all)

    await engine.dispose()
    print("All tables created successfully!")


if __name__ == "__main__":
    asyncio.run(create_tables())
