#!/usr/bin/env python3
"""Create a test user for E2E testing."""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User
from app.services.database import database_service


async def create_test_user():
    """Create a test user for E2E testing."""
    print("Creating test user...")

    # Initialize database
    await database_service.connect()

    try:
        async with database_service.get_session() as session:
            # Check if test user already exists
            from sqlalchemy import select
            result = await session.execute(
                select(User).where(User.email == "test@e2e.local")
            )
            existing_user = result.scalar_one_or_none()

            if existing_user:
                print(f"✅ Test user already exists: ID={existing_user.id}, email={existing_user.email}")
                print(f"   Gmail connected: {existing_user.gmail_connected}")
                print(f"   Telegram connected: {existing_user.telegram_connected}")
                print(f"   Onboarding completed: {existing_user.onboarding_completed}")
                return existing_user.id

            # Create new test user
            test_user = User(
                email="test@e2e.local",
                hashed_password=get_password_hash("TestPassword123!"),
                gmail_connected=True,
                telegram_connected=False,
                onboarding_completed=False,
                is_active=True,
            )

            session.add(test_user)
            await session.commit()
            await session.refresh(test_user)

            print(f"✅ Test user created successfully!")
            print(f"   ID: {test_user.id}")
            print(f"   Email: {test_user.email}")
            print(f"   Password: TestPassword123!")
            print(f"\n🔐 Use these credentials for E2E testing")

            return test_user.id

    finally:
        await database_service.disconnect()


if __name__ == "__main__":
    user_id = asyncio.run(create_test_user())
    print(f"\n✅ Test user ready: ID={user_id}")
