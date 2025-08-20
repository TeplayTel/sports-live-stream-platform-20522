"""
Initialize or upgrade the database schema to the latest version using Alembic.

This script upgrades the database to 'head' by invoking the project's Alembic configuration.
It replaces the older behavior of direct Base.metadata.create_all() to avoid conflicts with
types, enums, and versioned schema changes.

Usage:
    python init_db.py
"""
import asyncio

# PUBLIC_INTERFACE
async def main():
    """Run Alembic migrations to upgrade database schema to latest (head)."""
    from src.database.connection import run_migrations
    await run_migrations()

if __name__ == "__main__":
    asyncio.run(main())
