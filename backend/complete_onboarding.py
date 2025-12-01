import asyncio
from app.utils.auth import create_access_token

async def main():
    # Create JWT token for user_id=2 (using thread_id "2")
    token_obj = create_access_token(thread_id="2")
    print(token_obj.access_token)

if __name__ == "__main__":
    asyncio.run(main())
