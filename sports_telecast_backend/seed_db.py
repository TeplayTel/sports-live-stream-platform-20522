from src.database.seed import seed_database
import asyncio

if __name__ == "__main__":
    # All DB connections must be configured via DATABASE_URL or POSTGRES_URL environment variable.
    asyncio.run(seed_database())
