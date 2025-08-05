#!/usr/bin/env python3
"""
Database management CLI for Sports Telecast Backend

This script provides commands for database initialization, seeding, and management.
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import (
    init_database, 
    check_database_connection, 
    get_database_health,
    close_database_connections
)
from src.database.seed import seed_database

async def init_db():
    """Initialize database tables"""
    print("🔧 Initializing database...")
    try:
        await init_database()
        print("✅ Database initialized successfully!")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False
    return True

async def check_db():
    """Check database connection"""
    print("🔍 Checking database connection...")
    try:
        if await check_database_connection():
            health = await get_database_health()
            print("✅ Database connection successful!")
            print(f"   Database: {health.get('database', 'N/A')}")
            print(f"   Host: {health.get('host', 'N/A')}")
            print(f"   Port: {health.get('port', 'N/A')}")
            print(f"   Status: {health.get('status', 'N/A')}")
        else:
            print("❌ Database connection failed!")
            return False
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False
    return True

async def seed_db():
    """Seed database with sample data"""
    print("🌱 Seeding database...")
    try:
        await seed_database()
        print("✅ Database seeded successfully!")
    except Exception as e:
        print(f"❌ Database seeding failed: {e}")
        return False
    return True

async def setup_db():
    """Complete database setup (init + seed)"""
    print("🚀 Setting up database...")
    
    # Check connection first
    if not await check_db():
        return False
    
    # Initialize tables
    if not await init_db():
        return False
    
    # Seed with sample data
    if not await seed_db():
        return False
    
    print("🎉 Database setup completed successfully!")
    return True

async def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="Database management for Sports Telecast Backend")
    parser.add_argument(
        "command",
        choices=["init", "seed", "check", "setup"],
        help="Database command to execute"
    )
    
    args = parser.parse_args()
    
    success = False
    
    try:
        if args.command == "init":
            success = await init_db()
        elif args.command == "seed":
            success = await seed_db()
        elif args.command == "check":
            success = await check_db()
        elif args.command == "setup":
            success = await setup_db()
        
    except KeyboardInterrupt:
        print("\n⚠️ Operation cancelled by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        await close_database_connections()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
